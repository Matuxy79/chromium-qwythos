//! Database model types matching the existing SQLAlchemy/Alembic schema.

use chrono::Utc;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// User record — mirrors `qwythos.models.users.User`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct User {
    pub id: String,
    pub name: String,
    pub email: String,
    pub role: String,
    pub profile_image_url: Option<String>,
    pub api_key: Option<String>,
    pub created_at: Option<i64>,
    pub updated_at: Option<i64>,
    pub last_active_at: Option<i64>,
    pub settings: Option<String>,
    pub info: Option<String>,
    pub oauth_sub: Option<String>,
}

impl User {
    /// Create a new user with generated ID and timestamps.
    pub fn new(name: &str, email: &str, role: &str) -> Self {
        let now = Utc::now().timestamp();
        Self {
            id: Uuid::new_v4().to_string(),
            name: name.to_string(),
            email: email.to_string(),
            role: role.to_string(),
            profile_image_url: Some("/user.png".to_string()),
            api_key: None,
            created_at: Some(now),
            updated_at: Some(now),
            last_active_at: Some(now),
            settings: None,
            info: None,
            oauth_sub: None,
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

/// JWT claims payload.
#[derive(Debug, Serialize, Deserialize)]
pub struct Claims {
    /// User ID
    pub sub: String,
    /// Expiration timestamp (Unix)
    pub exp: usize,
    /// Issued at timestamp (Unix)
    pub iat: usize,
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
