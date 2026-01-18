# Plan: Add Date Filtering for Posts from Apify API

## Problem
Posts returned from Apify API sometimes have timestamps from a long time ago, even though we pass date range parameters (days_back=1). The API doesn't always respect the date filters, so we need client-side validation.

## Analysis
Current situation:
- Date parameters are passed to Apify API in `apify_twitter_client.py`:
  - Line 62-63: `start` and `end` date in `get_user_tweets()`
  - Line 151: `since` and `until` in search query for `get_batch_tweets()`
- Posts are mapped in `_map_apify_to_standard()` (lines 224-313)
- No client-side date validation after receiving posts

## Solution
Add client-side date filtering to ensure all returned posts are within the expected date range (days_back parameter).

## Tasks
- [ ] Add date validation helper method in `apify_twitter_client.py`
  - Create `_is_within_date_range()` method to check if post timestamp is within expected range
  - Accept post_time, start_date, end_date as parameters
  - Return True/False

- [ ] Update `get_user_tweets()` method to filter posts by date
  - After mapping posts in lines 98-105, filter by date range
  - Log warning when posts outside date range are found
  - Only return posts within the expected date range (start_date to end_date)

- [ ] Update `get_batch_tweets()` method to filter posts by date
  - After mapping posts in lines 188-206, filter by date range
  - Log warning when posts outside date range are found
  - Only return posts within the expected date range

- [ ] Add logging to track filtered posts
  - Log count of posts filtered due to date mismatch
  - Log sample of out-of-range dates for debugging

- [ ] Test the changes (if possible)

- [ ] Commit and push changes to `claude/filter-posts-by-date-pXZA8`

## Implementation Notes
- Parse post_time (ISO 8601 format) to datetime for comparison
- Handle timezone-aware comparisons (all times are UTC)
- Keep the existing API parameters - filtering is additional safety layer
- This is a defensive approach: API should filter, but we validate client-side
