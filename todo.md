# Plan: Update Telegram Bot Link Formatting

## Problem
Currently, the entire post content/sentence is wrapped in a hyperlink. User wants to display the content as plain text and add a link at the end instead.

Example:
- Current: `<a href="url">Sanctum announced a small seed extension round...</a>`
- Desired: `Sanctum announced a small seed extension round... [Link](url)` or `Sanctum announced... url`

## Tasks
- [ ] Update `_format_posts_for_ai` method in `services/report_generator.py` (line 156)
  - Change from: `<a href="{link_url}">{content}</a>`
  - Change to: `{content} <a href="{link_url}">Link</a>`

- [ ] Update `_generate_simple_summary` method in `services/report_generator.py` (line 180)
  - Change from: `<a href="{link_url}">{content}...</a>`
  - Change to: `{content}... <a href="{link_url}">Link</a>`

- [ ] Test the changes locally (optional, if testing environment available)

- [ ] Commit changes with clear message

- [ ] Push to branch `claude/update-funding-info-U15EL`

## Notes
- Using HTML `<a>` tags since Telegram parse_mode is set to "HTML"
- Keeping author links unchanged (line 174) - only modifying content links
