import { requestApi } from './api';
import { TwitterAuth } from './auth';
import { ApiError } from './errors';
import { TimelineInstruction } from './timeline-v2';

export interface HomeLatestTimelineResponse {
  data?: {
    home: {
      home_timeline_urt: {
        instructions: TimelineInstruction[];
      };
    };
  };
}

export async function fetchFollowingTimeline(
  count: number,
  seenTweetIds: string[],
  auth: TwitterAuth,
): Promise<any[]> {
  const variables = {
    count,
    includePromotedContent: true,
    latestControlAvailable: true,
    requestContext: 'launch',
    seenTweetIds,
  };

  const features = {
    profile_label_improvements_pcf_label_in_post_enabled: true,
    rweb_tipjar_consumption_enabled: true,
    responsive_web_graphql_exclude_directive_enabled: true,
    verified_phone_label_enabled: false,
    creator_subscriptions_tweet_preview_api_enabled: true,
    responsive_web_graphql_timeline_navigation_enabled: true,
    responsive_web_graphql_skip_user_profile_image_extensions_enabled: false,
    communities_web_enable_tweet_community_results_fetch: true,
    c9s_tweet_anatomy_moderator_badge_enabled: true,
    articles_preview_enabled: true,
    responsive_web_edit_tweet_api_enabled: true,
    graphql_is_translatable_rweb_tweet_is_translatable_enabled: true,
    view_counts_everywhere_api_enabled: true,
    longform_notetweets_consumption_enabled: true,
    responsive_web_twitter_article_tweet_consumption_enabled: true,
    tweet_awards_web_tipping_enabled: false,
    creator_subscriptions_quote_tweet_preview_enabled: false,
    freedom_of_speech_not_reach_fetch_enabled: true,
    standardized_nudges_misinfo: true,
    tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled:
      true,
    rweb_video_timestamps_enabled: true,
    longform_notetweets_rich_text_read_enabled: true,
    longform_notetweets_inline_media_enabled: true,
    responsive_web_enhance_cards_enabled: false,
  };

  const res = await requestApi<HomeLatestTimelineResponse>(
    `https://x.com/i/api/graphql/K0X1xbCZUjttdK8RazKAlw/HomeLatestTimeline?variables=${encodeURIComponent(
      JSON.stringify(variables),
    )}&features=${encodeURIComponent(JSON.stringify(features))}`,
    auth,
    'GET',
  );

  if (!res.success) {
    if (res.err instanceof ApiError) {
      console.error('Error details:', res.err.data);
    }
    throw res.err;
  }

  const home = res.value?.data?.home.home_timeline_urt?.instructions;

  if (!home) {
    return [];
  }

  const entries: any[] = [];

  for (const instruction of home) {
    if (instruction.type === 'TimelineAddEntries') {
      for (const entry of instruction.entries ?? []) {
        entries.push(entry);
      }
    }
  }
  // get the itemContnent from each entry
  const tweets = entries
    .map((entry) => entry.content.itemContent?.tweet_results?.result)
    .filter((tweet) => tweet !== undefined);

  return tweets;
}
