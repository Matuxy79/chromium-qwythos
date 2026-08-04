//! Database connection pool and migration runner.

pub mod models;

use sqlx::any::{AnyPool, AnyPoolOptions};
use std::time::Duration;

/// Thin wrapper around the sqlx connection pool.
#[derive(Debug, Clone)]
pub struct Database {
    pub pool: AnyPool,
}

impl Database {
    /// Connect to the database using the provided URL.
    ///
    /// Supported schemes: `sqlite:`, `postgres://`, `postgresql://`
    pub async fn connect(database_url: &str) -> anyhow::Result<Self> {
        // Install all sqlx drivers we compiled with
        sqlx::any::install_default_drivers();

        let pool = AnyPoolOptions::new()
            .max_connections(25)
            .min_connections(2)
            .acquire_timeout(Duration::from_secs(10))
            .idle_timeout(Duration::from_secs(300))
            .connect(database_url)
            .await?;

        Ok(Self { pool })
    }

    /// Run pending migrations.
    ///
    /// For Phase 0 this creates the core `users` and `auths` tables
    /// if they don't already exist (matching the existing Alembic schema).
    pub async fn run_migrations(&self) -> anyhow::Result<()> {
        // We use raw SQL to create tables if not exists, maintaining
        // compatibility with the existing Python/Alembic schema.
        // In production, this would use sqlx::migrate! macro with
        // proper migration files.
        sqlx::query(
            r#"
            CREATE TABLE IF NOT EXISTS "user" (
                id              TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                email           TEXT NOT NULL UNIQUE,
                role            TEXT NOT NULL DEFAULT 'pending',
                profile_image_url TEXT DEFAULT '/user.png',
                api_key         TEXT,
                created_at      BIGINT,
                updated_at      BIGINT,
                last_active_at  BIGINT,
                settings        TEXT,
                info            TEXT,
                oauth_sub       TEXT
            );
            "#,
        )
        .execute(&self.pool)
        .await?;

        sqlx::query(
            r#"
            CREATE TABLE IF NOT EXISTS auth (
                id              TEXT PRIMARY KEY,
                email           TEXT NOT NULL UNIQUE,
                password        TEXT NOT NULL,
                active          BOOLEAN NOT NULL DEFAULT true
            );
            "#,
        )
        .execute(&self.pool)
        .await?;

        Ok(())
    }
}
