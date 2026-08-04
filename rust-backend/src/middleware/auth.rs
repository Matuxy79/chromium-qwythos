//! JWT authentication middleware.
//!
//! Extracts and validates Bearer tokens from the Authorization header,
//! compatible with tokens issued by the existing Python backend.

use axum::{
    extract::{FromRequestParts, State},
    http::request::Parts,
};
use jsonwebtoken::{decode, DecodingKey, Validation};

use crate::db::models::{Claims, User};
use crate::error::AppError;
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
        let auth_header = parts
            .headers
            .get("authorization")
            .and_then(|v| v.to_str().ok())
            .ok_or_else(|| AppError::Unauthorized("Missing authorization header".into()))?;

        let token = auth_header
            .strip_prefix("Bearer ")
            .ok_or_else(|| AppError::Unauthorized("Invalid authorization format".into()))?;

        // Decode and validate JWT
        let key = DecodingKey::from_secret(state.config.jwt_secret.as_bytes());
        let mut validation = Validation::default();
        validation.validate_exp = true;

        let token_data = decode::<Claims>(token, &key, &validation)?;

        // Look up user in database
        let user_id = &token_data.claims.sub;

        let row = sqlx::query_as!(
            UserRow,
            r#"SELECT id, name, email, role, profile_image_url, api_key,
                      created_at, updated_at, last_active_at, settings, info, oauth_sub
               FROM "user" WHERE id = $1"#,
            user_id
        );

        // Since we use AnyPool, we fall back to a simpler query approach
        let user = sqlx::query(
            r#"SELECT id, name, email, role, profile_image_url, api_key,
                      created_at, updated_at, last_active_at, settings, info, oauth_sub
               FROM "user" WHERE id = ?"#,
        )
        .bind(user_id)
        .fetch_optional(&state.db.pool)
        .await
        .map_err(|e| AppError::Internal(e.into()))?
        .ok_or_else(|| AppError::Unauthorized("User not found".into()))?;

        use sqlx::Row;
        let user = User {
            id: user.try_get("id").unwrap_or_default(),
            name: user.try_get("name").unwrap_or_default(),
            email: user.try_get("email").unwrap_or_default(),
            role: user.try_get("role").unwrap_or_default(),
            profile_image_url: user.try_get("profile_image_url").ok(),
            api_key: user.try_get("api_key").ok(),
            created_at: user.try_get("created_at").ok(),
            updated_at: user.try_get("updated_at").ok(),
            last_active_at: user.try_get("last_active_at").ok(),
            settings: user.try_get("settings").ok(),
            info: user.try_get("info").ok(),
            oauth_sub: user.try_get("oauth_sub").ok(),
        };

        Ok(AuthUser(user))
    }
}

/// Lightweight extractor that only validates the token without DB lookup.
/// Use for high-frequency endpoints where user data isn't needed.
pub struct ValidToken(pub Claims);

impl FromRequestParts<AppState> for ValidToken {
    type Rejection = AppError;

    async fn from_request_parts(
        parts: &mut Parts,
        state: &AppState,
    ) -> Result<Self, Self::Rejection> {
        let auth_header = parts
            .headers
            .get("authorization")
            .and_then(|v| v.to_str().ok())
            .ok_or_else(|| AppError::Unauthorized("Missing authorization header".into()))?;

        let token = auth_header
            .strip_prefix("Bearer ")
            .ok_or_else(|| AppError::Unauthorized("Invalid authorization format".into()))?;

        let key = DecodingKey::from_secret(state.config.jwt_secret.as_bytes());
        let mut validation = Validation::default();
        validation.validate_exp = true;

        let token_data = decode::<Claims>(token, &key, &validation)?;
        Ok(ValidToken(token_data.claims))
    }
}

// Internal helper struct for typed query (unused with AnyPool but
// left as documentation for when we migrate to compile-time checked queries)
#[allow(dead_code)]
struct UserRow {
    id: String,
    name: String,
    email: String,
    role: String,
    profile_image_url: Option<String>,
    api_key: Option<String>,
    created_at: Option<i64>,
    updated_at: Option<i64>,
    last_active_at: Option<i64>,
    settings: Option<String>,
    info: Option<String>,
    oauth_sub: Option<String>,
}
