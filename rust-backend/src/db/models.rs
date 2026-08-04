//! Database model types matching the existing SQLAlchemy/Alembic schema.

use chrono::Utc;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// User record — mirrors the subset of `qwythos.models.users.User` columns
/// the Rust backend currently needs (id/email/username/role/name/avatar +
/// timestamps). The real table has additional profile/status columns (bio,
/// gender, timezone, presence, JSON blobs, ...) that aren't read/written
/// here yet — extend as later migration phases need them.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct User {
    pub id: String,
    pub email: String,
    pub username: Option<String>,
    pub role: String,
    pub name: String,
    pub profile_image_url: Option<String>,
    pub last_active_at: Option<i64>,
    pub updated_at: Option<i64>,
    pub created_at: Option<i64>,
}

impl User {
    /// Create a new user with generated ID and timestamps.
    pub fn new(name: &str, email: &str, role: &str) -> Self {
        let now = Utc::now().timestamp();
        Self {
            id: Uuid::new_v4().to_string(),
            email: email.to_string(),
            username: None,
            role: role.to_string(),
            name: name.to_string(),
            profile_image_url: Some("/user.png".to_string()),
            last_active_at: Some(now),
            updated_at: Some(now),
            created_at: Some(now),
        }
    }
}

/// Auth record — mirrors `qwythos.models.auths.Auth`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Auth {
    pub id: String,
    pub email: String,
    pub password: String,
    pub active: bool,
}

/// JWT claims payload — matches `create_token`'s shape in
/// `qwythos/utils/auth.py` (`id`, `jti`, `iat`, `exp`) so tokens are
/// interchangeable between the Rust and Python backends.
#[derive(Debug, Serialize, Deserialize)]
pub struct Claims {
    /// User ID (named `id`, not `sub` — matches the Python backend's claim key)
    pub id: String,
    /// JWT ID, used for future per-token revocation (see Phase 6)
    pub jti: String,
    /// Issued-at timestamp (Unix seconds)
    pub iat: usize,
    /// Expiration timestamp (Unix seconds)
    pub exp: usize,
}

/// Sign-in request body.
#[derive(Debug, Deserialize)]
pub struct SignInRequest {
    pub email: String,
    pub password: String,
}

/// Sign-up request body.
#[derive(Debug, Deserialize)]
pub struct SignUpRequest {
    pub name: String,
    pub email: String,
    pub password: String,
}

/// Auth response returned on successful sign-in/sign-up.
#[derive(Debug, Serialize)]
pub struct AuthResponse {
    pub token: String,
    pub token_type: String,
    pub id: String,
    pub name: String,
    pub email: String,
    pub role: String,
    pub profile_image_url: String,
}

/// Model info returned from /api/v1/models.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelInfo {
    pub id: String,
    pub name: String,
    pub object: String,
    pub created: Option<i64>,
    pub owned_by: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub connection_idx: Option<usize>,
}

/// Response wrapper for model listing.
#[derive(Debug, Serialize)]
pub struct ModelsResponse {
    pub data: Vec<ModelInfo>,
    pub object: String,
}
