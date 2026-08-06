//! JWT authentication middleware.
//!
//! Extracts and validates Bearer tokens from the Authorization header,
//! compatible with tokens issued by the existing Python backend.

use axum::extract::FromRequestParts;
use axum::http::request::Parts;
use sqlx::Row;

use crate::db::models::{Claims, User};
use crate::error::AppError;
use crate::services::auth::decode_token;
use crate::AppState;

/// Extractor that validates the JWT and resolves the user from the database.
///
/// Usage in handlers:
/// ```rust
/// async fn my_handler(AuthUser(user): AuthUser) -> ... { }
/// ```
pub struct AuthUser(pub User);

impl FromRequestParts<AppState> for AuthUser {
    type Rejection = AppError;

    async fn from_request_parts(
        parts: &mut Parts,
        state: &AppState,
    ) -> Result<Self, Self::Rejection> {
        // Extract Bearer token from Authorization header
        let token = extract_bearer_token(parts)?;
        let claims = decode_token(&token, &state.config.jwt_secret)?;

        let row = sqlx::query(
            r#"SELECT id, email, username, role, name, profile_image_url,
                      last_active_at, updated_at, created_at
               FROM "user" WHERE id = ?"#,
        )
        .bind(&claims.id)
        .fetch_optional(&state.db.pool)
        .await
        .map_err(|e| AppError::Internal(e.into()))?
        .ok_or_else(|| AppError::Unauthorized("User not found".into()))?;

        let user = User {
            id: row.try_get("id").unwrap_or_default(),
            email: row.try_get("email").unwrap_or_default(),
            username: row.try_get("username").ok(),
            role: row.try_get("role").unwrap_or_default(),
            name: row.try_get("name").unwrap_or_default(),
            profile_image_url: row.try_get("profile_image_url").ok(),
            last_active_at: row.try_get("last_active_at").ok(),
            updated_at: row.try_get("updated_at").ok(),
            created_at: row.try_get("created_at").ok(),
        };

        Ok(AuthUser(user))
    }
}

/// Lightweight extractor that only validates the token without DB lookup.
/// Use for high-frequency endpoints where user data isn't needed.
pub struct ValidToken(pub Claims);

/// Lightweight extractor that only validates the token without a DB lookup.
/// Use for high-frequency endpoints where user data isn't needed.
pub struct ValidToken(pub Claims);

impl FromRequestParts<AppState> for ValidToken {
    type Rejection = AppError;

    async fn from_request_parts(parts: &mut Parts, state: &AppState) -> Result<Self, Self::Rejection> {
        let token = extract_bearer_token(parts)?;
        let claims = decode_token(&token, &state.config.jwt_secret)?;
        Ok(ValidToken(claims))
    }
}

fn extract_bearer_token(parts: &Parts) -> Result<String, AppError> {
    let auth_header = parts
        .headers
        .get("authorization")
        .and_then(|v| v.to_str().ok())
        .ok_or_else(|| AppError::Unauthorized("Missing authorization header".into()))?;

    auth_header
        .strip_prefix("Bearer ")
        .map(|s| s.to_string())
        .ok_or_else(|| AppError::Unauthorized("Invalid authorization format".into()))
}
