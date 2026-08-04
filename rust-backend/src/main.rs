//! Qwythos Rust Backend
//!
//! High-performance API server for authentication, model listing,
//! and streaming LLM chat completion proxying.
//!
//! Architecture:
//!   - `config`     — Environment variable and configuration loading
//!   - `db`         — Database connection pool and model definitions
//!   - `error`      — Unified error type for the application
//!   - `middleware`  — CORS, auth extraction, and request guards
//!   - `routes`     — HTTP route handlers (auth, chat, models, health)
//!   - `services`   — Business logic (auth, LLM proxy)

mod config;
mod db;
mod error;
mod middleware;
mod routes;
mod services;

use std::net::SocketAddr;
use std::time::Duration;

use axum::Router;
use tower_http::compression::CompressionLayer;
use tower_http::timeout::TimeoutLayer;
use tower_http::trace::TraceLayer;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

use crate::config::AppConfig;
use crate::db::Database;

/// Application state shared across all request handlers.
#[derive(Clone)]
pub struct AppState {
    pub config: AppConfig,
    pub db: Database,
    pub http_client: reqwest::Client,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // ── Logging ──────────────────────────────────────────────────────
    tracing_subscriber::registry()
        .with(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "qwythos_backend=debug,tower_http=debug".into()),
        )
        .with(tracing_subscriber::fmt::layer())
        .init();

    tracing::info!("Starting Qwythos Rust Backend...");

    // ── Configuration ────────────────────────────────────────────────
    dotenvy::dotenv().ok();
    let config = AppConfig::from_env()?;
    tracing::info!(host = %config.host, port = %config.port, "Configuration loaded");

    // ── Database ─────────────────────────────────────────────────────
    let db = Database::connect(&config.database_url).await?;
    db.run_migrations().await?;
    tracing::info!("Database connected and migrations applied");

    // ── HTTP Client (for LLM proxying) ───────────────────────────────
    let http_client = reqwest::Client::builder()
        .timeout(Duration::from_secs(300)) // 5 min timeout for LLM calls
        .pool_max_idle_per_host(20)
        .build()?;

    // ── App State ────────────────────────────────────────────────────
    let state = AppState {
        config: config.clone(),
        db,
        http_client,
    };

    // ── Router ───────────────────────────────────────────────────────
    let app = Router::new()
        .merge(routes::health::router())
        .nest("/api/v1", routes::api_router(state.clone()))
        .layer(middleware::cors::cors_layer(&config))
        .layer(CompressionLayer::new())
        .layer(TimeoutLayer::new(Duration::from_secs(600)))
        .layer(TraceLayer::new_for_http())
        .with_state(state);

    // ── Server ───────────────────────────────────────────────────────
    let addr = SocketAddr::new(config.host.parse()?, config.port);
    tracing::info!(%addr, "Qwythos Rust Backend listening");

    let listener = tokio::net::TcpListener::bind(addr).await?;

    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await?;

    tracing::info!("Server shut down gracefully");
    Ok(())
}

/// Wait for Ctrl+C or SIGTERM for graceful shutdown.
async fn shutdown_signal() {
    let ctrl_c = async {
        tokio::signal::ctrl_c()
            .await
            .expect("failed to install Ctrl+C handler");
    };

    #[cfg(unix)]
    let terminate = async {
        tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())
            .expect("failed to install signal handler")
            .recv()
            .await;
    };

    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();

    tokio::select! {
        _ = ctrl_c => tracing::info!("Received Ctrl+C, shutting down..."),
        _ = terminate => tracing::info!("Received SIGTERM, shutting down..."),
    }
}
