//! Application configuration loaded from environment variables.
//!
//! Mirrors the critical subset of `backend/qwythos/config.py` that the
//! Rust backend needs for Phase 0-2 (auth, model listing, chat proxy).

use serde::Deserialize;

/// Top-level application configuration.
#[derive(Debug, Clone, Deserialize)]
pub struct AppConfig {
    /// Server bind host (default: "0.0.0.0")
    pub host: String,
    /// Server bind port (default: 8080)
    pub port: u16,

    // ── Database ─────────────────────────────────────────────────────
    /// SQLx-compatible database URL
    /// Examples:
    ///   sqlite:./data/qwythos.db
    ///   postgres://user:pass@localhost/qwythos
    pub database_url: String,

    // ── Auth ─────────────────────────────────────────────────────────
    /// Secret key for JWT signing (matches WEBUI_SECRET_KEY)
    pub jwt_secret: String,
    /// JWT token expiry in hours (default: 72)
    pub jwt_expiry_hours: u64,

    // ── LLM Connections ──────────────────────────────────────────────
    /// Comma-separated OpenAI-compatible API base URLs
    /// e.g. "https://api.openai.com/v1,http://localhost:11434/v1"
    pub openai_api_base_urls: Vec<String>,
    /// Corresponding API keys (same order as base URLs, use "" for keyless)
    pub openai_api_keys: Vec<String>,

    /// Ollama base URL (if separate from OpenAI endpoints)
    pub ollama_base_url: Option<String>,

    // ── CORS ─────────────────────────────────────────────────────────
    /// Comma-separated allowed origins (default: "*")
    pub cors_allow_origins: Vec<String>,

    // ── Council ──────────────────────────────────────────────────────
    /// Whether the LLM Council feature is enabled
    pub enable_council: bool,
    /// Comma-separated model IDs for council
    pub council_models: Vec<String>,
    /// Chairman model ID for council synthesis
    pub council_chairman_model: Option<String>,
}

impl AppConfig {
    /// Load configuration from environment variables with sensible defaults.
    pub fn from_env() -> anyhow::Result<Self> {
        let get = |key: &str| std::env::var(key).ok();
        let get_or = |key: &str, default: &str| {
            std::env::var(key).unwrap_or_else(|_| default.to_string())
        };

        let split_csv = |val: &str| -> Vec<String> {
            val.split(',')
                .map(|s| s.trim().to_string())
                .filter(|s| !s.is_empty())
                .collect()
        };

        Ok(Self {
            host: get_or("HOST", "0.0.0.0"),
            port: get_or("PORT", "8080").parse()?,
            database_url: get_or(
                "DATABASE_URL",
                "sqlite://../backend/data/webui.db",
            ),
            jwt_secret: resolve_jwt_secret()?,
            jwt_expiry_hours: get_or("JWT_EXPIRY_HOURS", "72").parse()?,
            openai_api_base_urls: get("OPENAI_API_BASE_URLS")
                .map(|v| split_csv(&v))
                .unwrap_or_default(),
            openai_api_keys: get("OPENAI_API_KEYS")
                .map(|v| split_csv(&v))
                .unwrap_or_default(),
            ollama_base_url: get("OLLAMA_BASE_URL"),
            cors_allow_origins: get("CORS_ALLOW_ORIGIN")
                .map(|v| split_csv(&v))
                .unwrap_or_else(|| vec!["*".to_string()]),
            enable_council: get_or("ENABLE_COUNCIL", "true")
                .to_lowercase()
                == "true",
            council_models: get("COUNCIL_MODELS")
                .map(|v| split_csv(&v))
                .unwrap_or_default(),
            council_chairman_model: get("COUNCIL_CHAIRMAN_MODEL"),
        })
    }
}

/// Resolves the JWT signing secret the same way `start_windows.bat` /
/// `qwythos/env.py` do: prefer `WEBUI_SECRET_KEY`, then
/// `WEBUI_JWT_SECRET_KEY`, then the contents of `.webui_secret_key` next to
/// the Python backend — so tokens stay valid across both services during
/// the migration instead of silently signing with an insecure default.
fn resolve_jwt_secret() -> anyhow::Result<String> {
    if let Ok(key) = std::env::var("WEBUI_SECRET_KEY") {
        if !key.is_empty() {
            return Ok(key);
        }
    }
    if let Ok(key) = std::env::var("WEBUI_JWT_SECRET_KEY") {
        if !key.is_empty() {
            return Ok(key);
        }
    }

    let key_file =
        std::env::var("WEBUI_SECRET_KEY_FILE").unwrap_or_else(|_| "../backend/.webui_secret_key".to_string());

    std::fs::read_to_string(&key_file).map(|s| s.trim().to_string()).map_err(|e| {
        anyhow::anyhow!(
            "WEBUI_SECRET_KEY is not set and {key_file} could not be read: {e}. \
             Set WEBUI_SECRET_KEY, or run the Python backend once to generate {key_file}."
        )
    })
}
