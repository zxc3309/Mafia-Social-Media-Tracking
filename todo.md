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
- [x] Add date validation helper method in `apify_twitter_client.py`
  - Create `_is_within_date_range()` method to check if post timestamp is within expected range
  - Accept post_time, start_date, end_date as parameters
  - Return True/False

- [x] Update `get_user_tweets()` method to filter posts by date
  - After mapping posts in lines 98-105, filter by date range
  - Log warning when posts outside date range are found
  - Only return posts within the expected date range (start_date to end_date)

- [x] Update `get_batch_tweets()` method to filter posts by date
  - After mapping posts in lines 188-206, filter by date range
  - Log warning when posts outside date range are found
  - Only return posts within the expected date range

- [x] Add logging to track filtered posts
  - Log count of posts filtered due to date mismatch
  - Log sample of out-of-range dates for debugging

- [x] Commit and push changes to `claude/filter-posts-by-date-pXZA8`

## Implementation Notes
- Parse post_time (ISO 8601 format) to datetime for comparison
- Handle timezone-aware comparisons (all times are UTC)
- Keep the existing API parameters - filtering is additional safety layer
- This is a defensive approach: API should filter, but we validate client-side

## Review

### Changes Made
All changes were made to `clients/apify_twitter_client.py`:

1. **Added `_is_within_date_range()` helper method** (lines 224-250)
   - Validates if a post's timestamp falls within the specified date range
   - Handles timezone-aware datetime comparisons
   - Returns True/False; defaults to True if parsing fails (conservative approach)

2. **Updated `get_user_tweets()` method** (lines 116-130)
   - Added client-side filtering after mapping posts
   - Filters out posts with timestamps outside the date range
   - Logs warning with count of filtered posts
   - Returns only posts within the expected date range

3. **Updated `get_batch_tweets()` method** (lines 200, 213-218, 237-238)
   - Added out_of_range_count tracking
   - Filters posts during the mapping loop
   - Logs warning with total count of filtered posts across all users
   - Only adds posts within date range to results_by_user dictionary

### Impact
- **Files modified**: 1 (`clients/apify_twitter_client.py`)
- **Lines added**: ~53
- **Breaking changes**: None
- **Backward compatible**: Yes - only adds additional filtering

### Benefits
- Ensures all posts returned match the requested time window (days_back parameter)
- Provides visibility when Apify API returns out-of-range posts (via warning logs)
- Prevents processing of irrelevant old posts
- No breaking changes - existing code continues to work

### Testing Recommendations
- Monitor logs for "Filtered N tweets outside date range" warnings
- Verify that posts displayed match the expected time period
- Check if filtering reduces the number of irrelevant posts

### Commit
- Branch: `claude/filter-posts-by-date-pXZA8`
- Commit: ee5bd74
- Message: "Add client-side date filtering for Apify posts"
