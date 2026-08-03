//! Rust streaming-proxy slice: Axum + reqwest.
//!
//! Does the same work as bench/py_proxy.py -- accept an OpenAI-compatible
//! chat-completions request, forward it to the upstream over a pooled client,
//! and stream the SSE response straight back to the caller.

use axum::{
    body::{Body, Bytes},
    extract::State,
    http::{header, StatusCode},
    response::{IntoResponse, Response},
    routing::{get, post},
    Router,
};
use bytes::BytesMut;
use futures_util::StreamExt;
use std::env;

#[derive(Clone)]
struct AppState {
    client: reqwest::Client,
    upstream: String,
}

async fn chat_completions(State(st): State<AppState>, body: Bytes) -> Response {
    match st
        .client
        .post(&st.upstream)
        .header(header::CONTENT_TYPE, "application/json")
        .body(body)
        .send()
        .await
    {
        Ok(resp) => {
            let status = StatusCode::from_u16(resp.status().as_u16()).unwrap_or(StatusCode::OK);

            // Coalesce chunks that are ALREADY ready into a single write, matching
            // what aiohttp's iter_any() does opportunistically. `ready_chunks` never
            // awaits for more, so this adds no latency -- it only avoids emitting one
            // HTTP frame + syscall per SSE event.
            let stream = resp.bytes_stream().ready_chunks(64).map(
                |chunks: Vec<Result<Bytes, reqwest::Error>>| -> Result<Bytes, reqwest::Error> {
                    let mut buf = BytesMut::new();
                    for chunk in chunks {
                        buf.extend_from_slice(&chunk?);
                    }
                    Ok(buf.freeze())
                },
            );

            Response::builder()
                .status(status)
                .header(header::CONTENT_TYPE, "text/event-stream")
                .header(header::CACHE_CONTROL, "no-cache")
                .body(Body::from_stream(stream))
                .unwrap()
        }
        Err(e) => (StatusCode::BAD_GATEWAY, format!("upstream error: {e}")).into_response(),
    }
}

async fn health() -> &'static str {
    "{\"status\":true}"
}

fn main() {
    // BENCH_THREADS=1 -> current-thread runtime, the apples-to-apples match for
    // asyncio's single-threaded loop. Unset/0 -> Tokio's default multi-thread.
    let threads: usize = env::var("BENCH_THREADS")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(0);

    let rt = if threads == 1 {
        tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .unwrap()
    } else {
        let mut builder = tokio::runtime::Builder::new_multi_thread();
        builder.enable_all();
        if threads > 0 {
            builder.worker_threads(threads);
        }
        builder.build().unwrap()
    };

    rt.block_on(async_main());
}

async fn async_main() {
    let upstream = env::var("BENCH_UPSTREAM")
        .unwrap_or_else(|_| "http://127.0.0.1:9100/v1/chat/completions".to_string());
    let port = env::var("BENCH_PORT").unwrap_or_else(|_| "9102".to_string());

    let state = AppState {
        client: reqwest::Client::new(),
        upstream,
    };

    let app = Router::new()
        .route("/v1/chat/completions", post(chat_completions))
        .route("/health", get(health))
        .with_state(state);

    let listener = tokio::net::TcpListener::bind(format!("127.0.0.1:{port}"))
        .await
        .unwrap();
    println!("rs_proxy listening on 127.0.0.1:{port} (pid {})", std::process::id());
    axum::serve(listener, app).await.unwrap();
}
