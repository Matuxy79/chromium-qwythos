//! CORS middleware configuration.

use tower_http::cors::{AllowOrigin, CorsLayer};
use axum::http::{HeaderValue, Method};

use crate::config::AppConfig;

/// Build a CORS layer matching the existing Python backend's CORS config.
pub fn cors_layer(config: &AppConfig) -> CorsLayer {
    let origins = &config.cors_allow_origins;

    let allow_origin = if origins.iter().any(|o| o == "*") {
        AllowOrigin::any()
    } else {
        let parsed: Vec<HeaderValue> = origins
            .iter()
            .filter_map(|o| o.parse().ok())
            .collect();
        AllowOrigin::list(parsed)
    };

    CorsLayer::new()
        .allow_origin(allow_origin)
        .allow_methods([
            Method::GET,
            Method::POST,
            Method::PUT,
            Method::PATCH,
            Method::DELETE,
            Method::OPTIONS,
        ])
        .allow_headers(tower_http::cors::Any)
        .allow_credentials(false)
        .max_age(std::time::Duration::from_secs(86400))
}
