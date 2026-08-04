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
    /// Against the real `backend/data/webui.db`, these `CREATE TABLE IF NOT
    /// EXISTS` statements are no-ops — that database's schema is owned by
    /// the Python backend's Alembic migrations. Against a fresh/dev
    /// database they bootstrap the subset of columns this Rust backend
    /// currently reads/writes, matching `qwythos.models.users.User` and
    /// `qwythos.models.auths.Auth` (the real tables have additional
    /// profile/status/JSON columns not needed yet — see db/models.rs).
    pub async fn run_migrations(&self) -> anyhow::Result<()> {
        sqlx::query(
            r#"
            CREATE TABLE IF NOT EXISTS "user" (
                id                 TEXT PRIMARY KEY,
                email              TEXT UNIQUE,
                username           TEXT,
                role               TEXT DEFAULT 'pending',
                name               TEXT NOT NULL,
                profile_image_url  TEXT,
                last_active_at     BIGINT,
                updated_at         BIGINT,
                created_at         BIGINT
            );
            "#,
        )
        .execute(&self.pool)
        .await?;

        sqlx::query(
            r#"
            CREATE TABLE IF NOT EXISTS auth (
                id       TEXT PRIMARY KEY,
                email    TEXT,
                password TEXT,
                active   BOOLEAN
            );
            "#,
        )
        .execute(&self.pool)
        .await?;

        Ok(())
    }
}
