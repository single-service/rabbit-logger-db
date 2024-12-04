CREATE DATABASE IF NOT EXISTS rabbit_logger;

CREATE TABLE IF NOT EXISTS rabbit_logger.apm
(
  uuid String,
  func_path Nullable(String),
  func_name Nullable(String),
  exec_time Nullable(Float64),
  cpu_used Nullable(Float64),
  ram_used Nullable(Float64),
  created_dt DateTime64(3),
  server_name Nullable(String)
)
ENGINE = MergeTree()
PARTITION BY toDate(created_dt)
ORDER BY (created_dt)
SETTINGS min_bytes_for_wide_part = 0;

CREATE TABLE IF NOT EXISTS rabbit_logger.logs
(
  uuid String,
  created_dt DateTime64(3),
  pathname Nullable(String),
  funcName Nullable(String),
  lineno Nullable(Int32),
  message Nullable(String),
  exc_text Nullable(String),
  created Nullable(Float64),
  filename Nullable(String),
  levelname Nullable(String),
  levelno Nullable(String),
  module Nullable(String),
  msecs Nullable(Float64),
  msg Nullable(String),
  name Nullable(String),
  process Nullable(String),
  processName Nullable(String),
  relativeCreated Nullable(String),
  stack_info Nullable(String),
  thread Nullable(String),
  threadName Nullable(String),
  server_name Nullable(String)
)
ENGINE = MergeTree()
PARTITION BY toDate(created_dt)
ORDER BY (created_dt)
SETTINGS min_bytes_for_wide_part = 0;
