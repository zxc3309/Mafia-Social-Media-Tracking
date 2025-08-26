#!/usr/bin/env node

const path = require('path');
const fs = require('fs');
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

// Import the compiled agent-twitter-client
const { Scraper } = require('./agent-twitter-client/dist/default/cjs/index.js');

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
            
            console.error(`Loaded ${cookieStrings.length} cookies from cache`);
            return cookieStrings;
        }
    } catch (error) {
        console.error('Error loading cookies:', error.message);
    }
    return [];
}

// Save cookies to file
async function saveCookies() {
    try {
        if (!scraper) return;
        
        const cookies = await scraper.getCookies();
        if (cookies && cookies.length > 0) {
            fs.writeFileSync(COOKIES_FILE, JSON.stringify(cookies, null, 2));
            console.error(`Saved ${cookies.length} cookies to cache`);
        }
    } catch (error) {
        console.error('Error saving cookies:', error.message);
    }
}

// Initialize scraper with authentication
async function initializeScraper() {
    try {
        if (!scraper) {
            scraper = new Scraper();
            const savedCookies = await loadCookies();
            
            if (savedCookies.length > 0) {
                await scraper.setCookies(savedCookies);
                console.error('Applied saved cookies to scraper');
            }
        }
        
        // Check if we need to login or refresh session
        const now = Date.now();
        const needsLogin = !isLoggedIn || !lastLoginTime || (now - lastLoginTime) > SESSION_DURATION;
        
        if (needsLogin) {
            console.error('Attempting to login to Twitter...');
            
            const username = process.env.TWITTER_USERNAME;
            const password = process.env.TWITTER_PASSWORD;
            const email = process.env.TWITTER_EMAIL;
            const totpSecret = process.env.TWITTER_2FA_SECRET;
            
            if (!username || !password) {
                throw new Error('Twitter credentials not provided in environment variables');
            }
            
            const loginResult = await scraper.login(username, password, email, totpSecret);
            
            // Check if login was actually successful (loginResult might be undefined)
            const actuallyLoggedIn = await scraper.isLoggedIn();
            
            if (actuallyLoggedIn) {
                console.error('✅ Successfully logged in to Twitter');
                isLoggedIn = true;
                lastLoginTime = now;
                
                // Save cookies after successful login
                await saveCookies();
            } else {
                const errorMsg = loginResult && loginResult.error ? loginResult.error : 'Login verification failed';
                console.error('❌ Login failed:', errorMsg);
                throw new Error(`Login failed: ${errorMsg}`);
            }
        } else {
            console.error('Using existing valid session');
        }
        
        return true;
    } catch (error) {
        console.error('Error initializing scraper:', error.message);
        throw error;
    }
}

// Get user tweets
async function getUserTweets(username, daysBack = 1) {
    try {
        await initializeScraper();
        
        console.error(`Fetching tweets for @${username} (last ${daysBack} days)...`);
        
        // Calculate time range
        const now = new Date();
        const startTime = new Date(now.getTime() - (daysBack * 24 * 60 * 60 * 1000));
        
        // Get user tweets
        const tweets = [];
        const maxTweets = 50; // Limit to avoid timeouts
        let tweetCount = 0;
        
        // Use search or profile tweets
        for await (const tweet of scraper.getTweets(username, maxTweets)) {
            if (tweetCount >= maxTweets) break;
            
            // Check if tweet is within time range
            // Use the correct time field (timeParsed or timestamp)
            const tweetTime = tweet.timeParsed ? new Date(tweet.timeParsed) : new Date(tweet.timestamp * 1000);
            if (tweetTime >= startTime) {
                tweets.push({
                    id: tweet.id_str || tweet.id,
                    content: tweet.full_text || tweet.text || '',
                    author: tweet.user?.screen_name || username,
                    post_time: tweetTime.toISOString(),
                    url: `https://twitter.com/${username}/status/${tweet.id_str || tweet.id}`,
                    retweet_count: tweet.retweet_count || 0,
                    favorite_count: tweet.favorite_count || 0,
                    reply_count: tweet.reply_count || 0
                });
            }
            tweetCount++;
        }
        
        console.error(`Successfully fetched ${tweets.length} tweets`);
        return tweets;
        
    } catch (error) {
        console.error('Error fetching tweets:', error.message);
        throw error;
    }
}

// Main CLI function
async function main() {
    try {
        // Parse command line arguments
        const args = process.argv.slice(2);
        
        if (args.length < 1) {
            console.error('Usage: node twitter_cli.js <username> [days_back]');
            console.error('Example: node twitter_cli.js elonmusk 1');
            process.exit(1);
        }
        
        const username = args[0].replace('@', ''); // Remove @ if present
        const daysBack = parseInt(args[1]) || 1;
        
        console.error(`Starting Twitter CLI for @${username}, ${daysBack} days back`);
        
        // Fetch tweets
        const tweets = await getUserTweets(username, daysBack);
        
        // Output result as JSON to stdout
        const result = {
            success: true,
            username: username,
            days_back: daysBack,
            tweets: tweets,
            timestamp: new Date().toISOString()
        };
        
        console.log(JSON.stringify(result, null, 2));
        
    } catch (error) {
        // Output error as JSON to stdout
        const result = {
            success: false,
            error: error.message,
            username: process.argv[2] || '',
            timestamp: new Date().toISOString()
        };
        
        console.log(JSON.stringify(result, null, 2));
        process.exit(1);
    }
}

// Handle graceful shutdown
process.on('SIGINT', async () => {
    console.error('\nShutting down gracefully...');
    await saveCookies();
    process.exit(0);
});

process.on('SIGTERM', async () => {
    console.error('\nShutting down gracefully...');
    await saveCookies();
    process.exit(0);
});

// Run the CLI
if (require.main === module) {
    main().catch(error => {
        console.error('Fatal error:', error);
        process.exit(1);
    });
}

module.exports = { getUserTweets };