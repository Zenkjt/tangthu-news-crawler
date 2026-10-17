# Phase 23 Fix 1 — VnExpress URL filter regression

## Problem
`test_vnexpress_selector_first_ignores_author_links` failed because Phase 23 moved non-article path filtering entirely into source YAML. The regression test uses a minimal VnExpress source config without `excluded_path_prefixes`, so `/tac-gia/...` was accepted by the fallback URL scan.

## Fix
Keep a small built-in VnExpress denylist for known non-article prefixes (`/tac-gia/`, `/author/`, `/chu-de/`, `/video/`), then append configured `excluded_path_prefixes`.

This preserves source-specific behavior while keeping the YAML denylist extensible for additional VnExpress page families such as `/tag/`, `/topic/`, `/search/`, etc.

## Scope
Discovery only. No changes to extractor, quality gate, BMP image conversion, EPUB rendering, or Drive upload.
