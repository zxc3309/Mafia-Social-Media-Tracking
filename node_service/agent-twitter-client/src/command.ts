// Declare the types for our custom global properties
declare global {
  var PLATFORM_NODE: boolean;
  var PLATFORM_NODE_JEST: boolean;
}

// Define platform constants before imports
globalThis.PLATFORM_NODE = typeof process !== 'undefined' && (
  // Node.js check
  (process.versions?.node != null) ||
  // Bun check
  (process.versions?.bun != null)
);
globalThis.PLATFORM_NODE_JEST = false;

// Your existing imports
import { Scraper } from './scraper';
import { Photo, Tweet } from './tweets';
import fs from 'fs';
import path from 'path';
import readline from 'readline';
import dotenv from 'dotenv';  

// Load environment variables from .env file
dotenv.config();

// Create a new Scraper instance
const scraper = new Scraper();

// Create readline interface for CLI
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  prompt: '> '
});

// Function to log in and save cookies
async function loginAndSaveCookies() {
  try {
    // Log in using credentials from environment variables
    await scraper.login(
      process.env.TWITTER_USERNAME!,
      process.env.TWITTER_PASSWORD!,
      process.env.TWITTER_EMAIL
    );

    // Retrieve the current session cookies
    const cookies = await scraper.getCookies();

    // Save the cookies to a JSON file for future sessions
    fs.writeFileSync(
      path.resolve(__dirname, 'cookies.json'),
      JSON.stringify(cookies)
    );

    console.log('Logged in and cookies saved.');
  } catch (error) {
    console.error('Error during login:', error);
  }
}

// Function to load cookies from the JSON file
async function loadCookies() {
  try {
    // Read cookies from the file system
    const cookiesData = fs.readFileSync(
      path.resolve(__dirname, 'cookies.json'),
      'utf8'
    );
    const cookiesArray = JSON.parse(cookiesData);

    // Map cookies to the correct format (strings)
    const cookieStrings = cookiesArray.map((cookie: any) => {
      return `${cookie.key}=${cookie.value}; Domain=${cookie.domain}; Path=${cookie.path}; ${
        cookie.secure ? 'Secure' : ''
      }; ${cookie.httpOnly ? 'HttpOnly' : ''}; SameSite=${
        cookie.sameSite || 'Lax'
      }`;
    });

    // Set the cookies for the current session
    await scraper.setCookies(cookieStrings);

    console.log('Cookies loaded from file.');
  } catch (error) {
    console.error('Error loading cookies:', error);
  }
}

// Function to ensure the scraper is authenticated
async function ensureAuthenticated() {
  // Check if cookies.json exists to decide whether to log in or load cookies
  if (fs.existsSync(path.resolve(__dirname, 'cookies.json'))) {
    // Load cookies if the file exists
    await loadCookies();

    // Inform the user that they are already logged in
    console.log('You are already logged in. No need to log in again.');
  } else {
    // Log in and save cookies if no cookie file is found
    await loginAndSaveCookies();
  }
}

// Function to send a tweet with optional media files
async function sendTweetCommand(
  text: string,
  mediaFiles?: string[],
  replyToTweetId?: string
): Promise<string | null> {
  try {
    let mediaData;

    if (mediaFiles && mediaFiles.length > 0) {
      // Prepare media data by reading files and determining media types
      mediaData = await Promise.all(
        mediaFiles.map(async (filePath) => {
          const absolutePath = path.resolve(__dirname, filePath);
          const buffer = await fs.promises.readFile(absolutePath);
          const ext = path.extname(filePath).toLowerCase();
          const mediaType = getMediaType(ext);
          return { data: buffer, mediaType };
        })
      );
    }

    // Send the tweet using the updated sendTweet function
    const response = await scraper.sendTweet(text, replyToTweetId, mediaData);

    // Parse the response to extract the tweet ID
    const responseData = await response.json();
    const tweetId =
      responseData?.data?.create_tweet?.tweet_results?.result?.rest_id;

    if (tweetId) {
      console.log(`Tweet sent: "${text}" (ID: ${tweetId})`);
      return tweetId;
    } else {
      console.error('Tweet ID not found in response.');
      return null;
    }
  } catch (error) {
    console.error('Error sending tweet:', error);
    return null;
  }
}

// Function to get media type based on file extension
function getMediaType(ext: string): string {
  switch (ext) {
    case '.jpg':
    case '.jpeg':
      return 'image/jpeg';
    case '.png':
      return 'image/png';
    case '.gif':
      return 'image/gif';
    case '.mp4':
      return 'video/mp4';
    // Add other media types as needed
    default:
      return 'application/octet-stream';
  }
}

// Function to get replies to a specific tweet
async function getRepliesToTweet(tweetId: string): Promise<Tweet[]> {
  const replies: Tweet[] = [];
  try {
    // Construct the search query to find replies
    const query = `to:${process.env.TWITTER_USERNAME} conversation_id:${tweetId}`;
    const maxReplies = 100; // Maximum number of replies to fetch
    const searchMode = 1; // SearchMode.Latest

    // Fetch replies matching the query
    for await (const tweet of scraper.searchTweets(query, maxReplies, searchMode)) {
      // Check if the tweet is a direct reply to the original tweet
      if (tweet.inReplyToStatusId === tweetId) {
        replies.push(tweet);
      }
    }

    console.log(`Found ${replies.length} replies to tweet ID ${tweetId}.`);
  } catch (error) {
    console.error('Error fetching replies:', error);
  }
  return replies;
}

// Function to reply to a specific tweet
async function replyToTweet(tweetId: string, text: string) {
  try {
    // Pass empty array for mediaFiles (2nd param) and tweetId as replyToTweetId (3rd param)
    const replyId = await sendTweetCommand(text, [], tweetId);

    if (replyId) {
      console.log(`Reply sent (ID: ${replyId}).`);
    }
  } catch (error) {
    console.error('Error sending reply:', error);
  }
}

// Function to get photos from a specific tweet
async function getPhotosFromTweet(tweetId: string) {
  try {
    // Fetch the tweet by its ID
    const tweet = await scraper.getTweet(tweetId);

    // Check if the tweet exists and contains photos
    if (tweet && tweet.photos.length > 0) {
      console.log(`Found ${tweet.photos.length} photo(s) in tweet ID ${tweetId}:`);
      // Iterate over each photo and display its URL
      tweet.photos.forEach((photo: Photo, index: number) => {
        console.log(`Photo ${index + 1}: ${photo.url}`);
      });
    } else {
      console.log('No photos found in the specified tweet.');
    }
  } catch (error) {
    console.error('Error fetching tweet:', error);
  }
}

// Function to parse command line while preserving quoted strings
function parseCommandLine(commandLine: string): string[] {
  const args: string[] = [];
  let currentArg = '';
  let inQuotes = false;

  for (let i = 0; i < commandLine.length; i++) {
    const char = commandLine[i];

    if (char === '"') {
      inQuotes = !inQuotes;
      continue;
    }

    if (char === ' ' && !inQuotes) {
      if (currentArg) {
        args.push(currentArg);
        currentArg = '';
      }
    } else {
      currentArg += char;
    }
  }

  if (currentArg) {
    args.push(currentArg);
  }

  return args;
}

// Function to execute commands
async function executeCommand(commandLine: string) {
  const args = parseCommandLine(commandLine);
  const command = args.shift(); // Remove and get the first element as command

  if (!command) return;

  switch (command) {
    case 'login':
      await loginAndSaveCookies();
      break;

    case 'send-tweet': {
      await ensureAuthenticated();

      // First argument is the tweet text
      const tweetText = args[0];
      // Remaining arguments are media file paths
      const mediaFiles = args.slice(1);

      if (!tweetText) {
        console.log('Please provide text for the tweet.');
      } else {
        // Call the sendTweetCommand with optional media files
        await sendTweetCommand(tweetText, mediaFiles);
      }
      break;
    }

    case 'send-long-tweet': {
      await ensureAuthenticated();

      // First argument is the tweet text
      const tweetText = args[0];
      // Remaining arguments are media file paths
      const mediaFiles = args.slice(1);

      if (!tweetText) {
        console.log('Please provide text for the long tweet.');
      } else {
        // Call the sendLongTweetCommand with optional media files
        await sendLongTweetCommand(tweetText, mediaFiles);
      }
      break;
    }

    case 'get-tweets':
      await ensureAuthenticated();
      const username = args[0];
      if (!username) {
        console.log('Please provide a username.');
      } else {
        try {
          const maxTweets = 20; // Maximum number of tweets to fetch
          const tweets: Tweet[] = [];
          for await (const tweet of scraper.getTweets(username, maxTweets)) {
            tweets.push(tweet);
          }
          console.log(`Fetched ${tweets.length} tweets from @${username}:`);
          tweets.forEach((tweet) => {
            console.log(`- [${tweet.id}] ${tweet.text}`);
          });
        } catch (error) {
          console.error('Error fetching tweets:', error);
        }
      }
      break;

    case 'get-replies': {
      await ensureAuthenticated();
      const tweetId = args[0];
      if (!tweetId) {
        console.log('Please provide a tweet ID.');
      } else {
        const replies = await getRepliesToTweet(tweetId);
        console.log(`Found ${replies.length} replies:`);
        replies.forEach((reply) => {
          console.log(`- @${reply.username}: ${reply.text}`);
        });
      }
      break;
    }

    case 'reply-to-tweet':
      await ensureAuthenticated();
      const replyTweetId = args[0];
      const replyText = args.slice(1).join(' ');
      if (!replyTweetId || !replyText) {
        console.log('Please provide a tweet ID and text to reply.');
      } else {
        await replyToTweet(replyTweetId, replyText);
      }
      break;

    case 'get-mentions':
      await ensureAuthenticated();
      try {
        const maxTweets = 20; // Maximum number of mentions to fetch
        const mentions: Tweet[] = [];
        const query = `@${process.env.TWITTER_USERNAME}`;
        const searchMode = 1; // SearchMode.Latest

        // Fetch recent mentions
        for await (const tweet of scraper.searchTweets(query, maxTweets, searchMode)) {
          // Exclude your own tweets
          if (tweet.username !== process.env.TWITTER_USERNAME) {
            mentions.push(tweet);
          }
        }
        console.log(`Found ${mentions.length} mentions:`);
        mentions.forEach((tweet) => {
          console.log(`- [${tweet.id}] @${tweet.username}: ${tweet.text}`);
        });

        // Fetch replies to each mention
        for (const mention of mentions) {
          // Get replies to the mention
          const replies = await getRepliesToTweet(mention.id!);
          console.log(`Replies to mention [${mention.id}] by @${mention.username}:`);
          replies.forEach((reply) => {
            console.log(`- [${reply.id}] @${reply.username}: ${reply.text}`);
          });
        }
      } catch (error) {
        console.error('Error fetching mentions:', error);
      }
      break;

    case 'help':
      console.log('Available commands:');
      console.log('  login                     - Login to Twitter and save cookies');
      console.log('  send-tweet <text> [mediaFiles...]       - Send a tweet with optional media attachments');
      console.log('  send-long-tweet <text> [mediaFiles...]  - Send a long tweet (Note Tweet) with optional media attachments');
      console.log('  get-tweets <username>     - Get recent tweets from the specified user');
      console.log('  get-replies <tweetId>     - Get replies to the specified tweet ID');
      console.log('  reply-to-tweet <tweetId> <text> - Reply to a tweet with the specified text');
      console.log('  get-mentions              - Get recent mentions of your account');
      console.log('  exit                      - Exit the application');
      console.log('  help                      - Show this help message');
      console.log('  send-quote-tweet <tweetId> "<text>" [mediaFiles...] - Send a quote tweet with optional media attachments');
      console.log('  get-photos <tweetId>      - Get photos from a specific tweet');
      console.log('  like <tweetId>            - Like a tweet by its ID');
      console.log('  retweet <tweetId>         - Retweet a tweet by its ID');
      console.log('  follow <username>         - Follow a user by their username');
      break;

    case 'exit':
      console.log('Exiting...');
      rl.close();
      process.exit(0);
      break;

    case 'get-photos': {
      await ensureAuthenticated();
      const tweetId = args[0];
      if (!tweetId) {
        console.log('Please provide a tweet ID.');
      } else {
        await getPhotosFromTweet(tweetId);
      }
      break;
    }

    case 'send-quote-tweet': {
      await ensureAuthenticated();

      if (args.length < 2) {
        console.log(
          'Usage: send-quote-tweet <tweetId> "<text>" [mediaFile1] [mediaFile2] ...'
        );
        break;
      }

      const quotedTweetId = args[0];
      const text = args[1];
      const mediaFiles = args.slice(2);

      // Prepare the quote tweet text including the quoted tweet URL
      const quoteTweetText = `${text} https://twitter.com/user/status/${quotedTweetId}`;

      // Send the quote tweet using the sendTweetCommand function
      await sendTweetCommand(quoteTweetText, mediaFiles);
      break;
    }

    case 'like':
      await ensureAuthenticated();
      const tweetId = args[0];
      if (!tweetId) {
        console.log('Please provide a tweet ID.');
      } else {
        try {
          // Attempt to like the tweet
          await scraper.likeTweet(tweetId);
          console.log(`Tweet ID ${tweetId} liked successfully.`);
        } catch (error) {
          console.error('Error liking tweet:', error);
        }
      }
      break;

    case 'retweet':
      await ensureAuthenticated();
      const retweetId = args[0];
      if (!retweetId) {
        console.log('Please provide a tweet ID.');
      } else {
        try {
          // Attempt to retweet the tweet
          await scraper.retweet(retweetId);
          console.log(`Tweet ID ${retweetId} retweeted successfully.`);
        } catch (error) {
          console.error('Error retweeting tweet:', error);
        }
      }
      break;

    case 'follow':
      await ensureAuthenticated();
      const usernameToFollow = args[0];
      if (!usernameToFollow) {
        console.log('Please provide a username to follow.');
      } else {
        try {
          // Attempt to follow the user
          await scraper.followUser(usernameToFollow);
          console.log(`Successfully followed user @${usernameToFollow}.`);
        } catch (error) {
          console.error('Error following user:', error);
        }
      }
      break;

    default:
      console.log(`Unknown command: ${command}. Type 'help' to see available commands.`);
      break;
  }
}

// Function to send a long tweet (Note Tweet) with optional media files
async function sendLongTweetCommand(
  text: string,
  mediaFiles?: string[],
  replyToTweetId?: string
): Promise<string | null> {
  try {
    let mediaData;

    if (mediaFiles && mediaFiles.length > 0) {
      // Prepare media data by reading files and determining media types
      mediaData = await Promise.all(
        mediaFiles.map(async (filePath) => {
          const absolutePath = path.resolve(__dirname, filePath);
          const buffer = await fs.promises.readFile(absolutePath);
          const ext = path.extname(filePath).toLowerCase();
          const mediaType = getMediaType(ext);
          return { data: buffer, mediaType };
        })
      );
    }

    // Send the long tweet using the sendLongTweet function
    const response = await scraper.sendLongTweet(text, replyToTweetId, mediaData);

    // Parse the response to extract the tweet ID
    const responseData = await response.json();
    const tweetId =
      responseData?.data?.notetweet_create?.tweet_results?.result?.rest_id;

    if (tweetId) {
      console.log(`Long tweet sent: "${text.substring(0, 50)}..." (ID: ${tweetId})`);
      return tweetId;
    } else {
      console.error('Tweet ID not found in response.');
      return null;
    }
  } catch (error) {
    console.error('Error sending long tweet:', error);
    return null;
  }
}

// Main function to start the CLI
(async () => {
  console.log('Welcome to the Twitter CLI Interface!');
  console.log("Type 'help' to see available commands.");
  rl.prompt();

  rl.on('line', async (line) => {
    await executeCommand(line);
    rl.prompt();
  }).on('close', () => {
    console.log('Goodbye!');
    process.exit(0);
  });
})();
