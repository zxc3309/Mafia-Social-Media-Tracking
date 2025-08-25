const express = require('express');
const cors = require('cors');
const morgan = require('morgan');
const path = require('path');
const fs = require('fs');
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

// Import the compiled agent-twitter-client
const { Scraper } = require('./agent-twitter-client/dist/default/cjs/index.js');

const app = express();
// Use AGENT_SERVICE_PORT or dynamic port (avoid Railway's main PORT)
const PORT = process.env.AGENT_SERVICE_PORT || 0; // 0 = dynamic port, don't use main app's PORT

// Middleware
app.use(cors());
app.use(express.json());
app.use(morgan('combined'));

// Global scraper instance and session management
let scraper = null;
let lastLoginTime = null;
let isLoggedIn = false;
const SESSION_DURATION = 6 * 60 * 60 * 1000; // 6 hours
const COOKIES_FILE = path.join(__dirname, '.twitter_cookies.json');

// Load saved cookies if they exist
async function loadCookies() {
    try {
        if (fs.existsSync(COOKIES_FILE)) {
            const cookiesData = fs.readFileSync(COOKIES_FILE, 'utf8');
            const cookiesArray = JSON.parse(cookiesData);
            
            // Convert JSON cookie objects to cookie strings that setCookies can understand
            const cookieStrings = cookiesArray.map(cookieObj => {
                // Create cookie string in format: "name=value; Domain=domain; Path=path; ..."
                let cookieString = `${cookieObj.key}=${cookieObj.value}`;
                
                if (cookieObj.domain) {
                    cookieString += `; Domain=${cookieObj.domain}`;
                }
                if (cookieObj.path) {
                    cookieString += `; Path=${cookieObj.path}`;
                }
                if (cookieObj.expires) {
                    cookieString += `; Expires=${cookieObj.expires}`;
                }
                if (cookieObj.secure) {
                    cookieString += `; Secure`;
                }
                if (cookieObj.httpOnly) {
                    cookieString += `; HttpOnly`;
                }
                if (cookieObj.sameSite) {
                    cookieString += `; SameSite=${cookieObj.sameSite}`;
                }
                
                return cookieString;
            });
            
            scraper = new Scraper();
            await scraper.setCookies(cookieStrings);
            
            // Verify the cookies are still valid
            const isValid = await scraper.isLoggedIn();
            if (isValid) {
                isLoggedIn = true;
                lastLoginTime = new Date();
                console.log('Successfully loaded saved cookies');
                return true;
            } else {
                console.log('Loaded cookies are invalid or expired');
            }
        }
    } catch (error) {
        console.error('Error loading cookies:', error.message);
        // If cookie loading fails, delete the invalid cookie file
        if (fs.existsSync(COOKIES_FILE)) {
            console.log('Removing invalid cookie file for fresh start');
            fs.unlinkSync(COOKIES_FILE);
        }
    }
    return false;
}

// Save cookies for future use
async function saveCookies() {
    try {
        if (scraper && isLoggedIn) {
            const cookies = await scraper.getCookies();
            fs.writeFileSync(COOKIES_FILE, JSON.stringify(cookies, null, 2));
            console.log('Cookies saved successfully');
        }
    } catch (error) {
        console.error('Error saving cookies:', error.message);
    }
}

// Initialize or refresh scraper session
async function initializeScraper() {
    try {
        // Check if we need to refresh the session
        if (isLoggedIn && lastLoginTime) {
            const timeSinceLogin = Date.now() - lastLoginTime.getTime();
            if (timeSinceLogin < SESSION_DURATION) {
                console.log('Using existing session');
                return true;
            }
        }

        // Try to load saved cookies first
        const cookiesLoaded = await loadCookies();
        if (cookiesLoaded) {
            return true;
        }

        // Create new scraper instance
        scraper = new Scraper();
        
        // Get credentials from environment
        const username = process.env.TWITTER_USERNAME;
        const password = process.env.TWITTER_PASSWORD;
        const email = process.env.TWITTER_EMAIL;
        const totpSecret = process.env.TWITTER_2FA_SECRET;
        
        if (!username || !password) {
            throw new Error('Twitter credentials not configured');
        }

        console.log(`Logging in as ${username}...`);
        
        // Perform login
        await scraper.login(username, password, email, totpSecret);
        
        isLoggedIn = true;
        lastLoginTime = new Date();
        
        // Save cookies for future use
        await saveCookies();
        
        console.log('Successfully logged in to Twitter');
        return true;
        
    } catch (error) {
        console.error('Failed to initialize scraper:', error.message);
        isLoggedIn = false;
        throw error;
    }
}

// Format tweet data to match Python client format
function formatTweet(tweet, username) {
    try {
        // Parse timestamp - handle Unix timestamp properly
        let postTime = null;
        if (tweet.timestamp) {
            // If timestamp looks like Unix seconds (less than year 3000), convert to milliseconds
            const ts = parseInt(tweet.timestamp);
            if (ts < 32503680000) { // Less than year 3000 in seconds
                postTime = new Date(ts * 1000).toISOString();
            } else {
                postTime = new Date(ts).toISOString();
            }
        } else if (tweet.timeParsed) {
            postTime = new Date(tweet.timeParsed).toISOString();
        }

        return {
            post_id: tweet.id || tweet.rest_id,
            username: tweet.username || username,
            display_name: tweet.name || tweet.username || username,
            content: tweet.text || '',
            post_time: postTime,
            post_url: `https://twitter.com/${tweet.username || username}/status/${tweet.id || tweet.rest_id}`,
            likes: parseInt(tweet.likes || tweet.favoriteCount || 0),
            retweets: parseInt(tweet.retweets || tweet.retweetCount || 0),
            replies: parseInt(tweet.replies || tweet.replyCount || 0),
            views: parseInt(tweet.views || tweet.viewCount || 0),
            platform: 'twitter',
            collection_method: 'agent',
            is_retweet: tweet.isRetweet || false,
            is_reply: tweet.isReply || false,
            media_urls: tweet.photos || [],
            hashtags: tweet.hashtags || []
        };
    } catch (error) {
        console.error('Error formatting tweet:', error);
        return null;
    }
}

// Get user tweets endpoint
app.post('/get_user_tweets', async (req, res) => {
    try {
        const { username, days_back = 1 } = req.body;
        
        if (!username) {
            return res.status(400).json({ 
                success: false, 
                error: 'Username is required' 
            });
        }

        // Ensure scraper is initialized
        await initializeScraper();
        
        console.log(`Fetching tweets for @${username} (last ${days_back} days)`);
        
        // Calculate the date range
        const endDate = new Date();
        const startDate = new Date();
        startDate.setDate(startDate.getDate() - days_back);
        
        // Fetch tweets
        const tweets = [];
        const maxTweets = 50; // Reasonable limit
        
        try {
            console.log(`Starting to fetch tweets for @${username}...`);
            let tweetCount = 0;
            
            // Use the async generator to fetch tweets
            for await (const tweet of scraper.getTweets(username, maxTweets)) {
                tweetCount++;
                console.log(`Processing tweet ${tweetCount}: ${tweet.id || 'no-id'} from ${tweet.timestamp || 'no-timestamp'}`);
                
                // Check if tweet is within date range
                if (tweet.timestamp) {
                    // Handle Unix timestamp properly
                    const ts = parseInt(tweet.timestamp);
                    const tweetDate = new Date(ts < 32503680000 ? ts * 1000 : ts);
                    if (tweetDate < startDate) {
                        console.log(`Tweet too old, stopping: ${tweetDate.toISOString()} < ${startDate.toISOString()}`);
                        break; // Stop if we've gone too far back
                    }
                    console.log(`Tweet date: ${tweetDate.toISOString()}, within range`);
                }
                
                const formattedTweet = formatTweet(tweet, username);
                if (formattedTweet) {
                    tweets.push(formattedTweet);
                    console.log(`Added tweet: ${formattedTweet.content.substring(0, 50)}...`);
                } else {
                    console.log(`Failed to format tweet:`, tweet);
                }
                
                // Limit to reasonable number of tweets
                if (tweets.length >= maxTweets) {
                    console.log(`Reached max tweets limit: ${maxTweets}`);
                    break;
                }
            }
            
            console.log(`Finished processing tweets. Found ${tweets.length} tweets from ${tweetCount} raw tweets.`);
        } catch (fetchError) {
            console.error('Error fetching tweets:', fetchError.message);
            
            // If it's an auth error, try to re-login
            if (fetchError.message.includes('auth') || fetchError.message.includes('login')) {
                isLoggedIn = false;
                await initializeScraper();
                
                // Retry once
                for await (const tweet of scraper.getTweets(username, maxTweets)) {
                    const formattedTweet = formatTweet(tweet, username);
                    if (formattedTweet) {
                        tweets.push(formattedTweet);
                    }
                    if (tweets.length >= maxTweets) {
                        break;
                    }
                }
            } else {
                throw fetchError;
            }
        }
        
        console.log(`Found ${tweets.length} tweets for @${username}`);
        
        // Filter tweets by date
        const filteredTweets = tweets.filter(tweet => {
            if (!tweet.post_time) return false;
            const tweetDate = new Date(tweet.post_time);
            return tweetDate >= startDate && tweetDate <= endDate;
        });
        
        console.log(`Returning ${filteredTweets.length} tweets within date range`);
        
        res.json({
            success: true,
            username: username,
            tweets: filteredTweets,
            count: filteredTweets.length
        });
        
    } catch (error) {
        console.error('Error in /get_user_tweets:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        isLoggedIn: isLoggedIn,
        lastLoginTime: lastLoginTime,
        uptime: process.uptime()
    });
});

// Test connection endpoint
app.get('/test', async (req, res) => {
    try {
        await initializeScraper();
        res.json({
            success: true,
            message: 'Twitter agent client is working',
            isLoggedIn: isLoggedIn
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('\nShutting down gracefully...');
    await saveCookies();
    process.exit(0);
});

process.on('SIGTERM', async () => {
    console.log('\nShutting down gracefully...');
    await saveCookies();
    process.exit(0);
});

// Start server
const server = app.listen(PORT, () => {
    const actualPort = server.address().port;
    console.log(`Twitter Agent Service running on http://localhost:${actualPort}`);
    console.log(`Actual port used: ${actualPort}`);
    console.log('Environment:', {
        username: process.env.TWITTER_USERNAME ? 'Set' : 'Not set',
        password: process.env.TWITTER_PASSWORD ? 'Set' : 'Not set',
        email: process.env.TWITTER_EMAIL ? 'Set' : 'Not set',
        totpSecret: process.env.TWITTER_2FA_SECRET ? 'Set' : 'Not set'
    });
    
    // Write port to file for Python service to read
    const fs = require('fs');
    try {
        fs.writeFileSync('.agent_service_port', actualPort.toString());
        console.log(`Port ${actualPort} written to .agent_service_port file`);
    } catch (err) {
        console.error('Failed to write port file:', err);
    }
});