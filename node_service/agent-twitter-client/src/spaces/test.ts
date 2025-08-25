// src/test.ts

import 'dotenv/config';
import { Space, SpaceConfig } from './core/Space';
import { Scraper } from '../scraper';
import { RecordToDiskPlugin } from './plugins/RecordToDiskPlugin';
import { SttTtsPlugin } from './plugins/SttTtsPlugin';
import { IdleMonitorPlugin } from './plugins/IdleMonitorPlugin';
import { HlsRecordPlugin } from './plugins/HlsRecordPlugin';

/**
 * Main test entry point
 */
async function main() {
  console.log('[Test] Starting...');

  // 1) Twitter login with your scraper
  const scraper = new Scraper();
  await scraper.login(
    process.env.TWITTER_USERNAME!,
    process.env.TWITTER_PASSWORD!,
  );

  // 2) Create the Space instance
  // Set debug=true if you want more logs
  const space = new Space(scraper, { debug: false });

  // --------------------------------------------------------------------------------
  // EXAMPLE 1: Record raw speaker audio via RecordToDiskPlugin (local plugin approach)
  // --------------------------------------------------------------------------------
  const recordPlugin = new RecordToDiskPlugin();
  space.use(recordPlugin);

  // --------------------------------------------------------------------------------
  // EXAMPLE 2: HLSRecordPlugin => record final Space mix as .ts file via HLS
  // (Requires the "scraper" to fetch the HLS URL, and ffmpeg installed.)
  // --------------------------------------------------------------------------------
  const hlsPlugin = new HlsRecordPlugin();
  // If you want, you can override the default output path in pluginConfig, for example:
  // space.use(hlsPlugin, { outputPath: '/tmp/my_custom_space.ts' });
  space.use(hlsPlugin);

  // Create our TTS/STT plugin instance
  const sttTtsPlugin = new SttTtsPlugin();
  space.use(sttTtsPlugin, {
    openAiApiKey: process.env.OPENAI_API_KEY,
    elevenLabsApiKey: process.env.ELEVENLABS_API_KEY,
    voiceId: 'D38z5RcWu1voky8WS1ja', // example
    // You can also initialize systemPrompt, chatContext, etc. here if you wish
    // systemPrompt: "You are a calm and friendly AI assistant."
  });

  // Create an IdleMonitorPlugin to stop after 60s of silence
  const idlePlugin = new IdleMonitorPlugin(60_000, 10_000);
  space.use(idlePlugin);

  // If idle occurs, say goodbye and end the Space
  space.on('idleTimeout', async (info) => {
    console.log(`[Test] idleTimeout => no audio for ${info.idleMs}ms.`);
    await sttTtsPlugin.speakText('Ending Space due to inactivity. Goodbye!');
    await new Promise((r) => setTimeout(r, 10_000));
    await space.stop();
    console.log('[Test] Space stopped due to silence.');
    process.exit(0);
  });

  // 3) Initialize the Space
  const config: SpaceConfig = {
    mode: 'INTERACTIVE',
    title: 'AI Chat - Dynamic GPT Config',
    description: 'Space that demonstrates dynamic GPT personalities.',
    languages: ['en'],
  };

  const broadcastInfo = await space.initialize(config);
  const spaceUrl = broadcastInfo.share_url.replace('broadcasts', 'spaces');
  console.log('[Test] Space created =>', spaceUrl);

  // (Optional) Tweet out the Space link
  await scraper.sendTweet(`${config.title} ${spaceUrl}`);
  console.log('[Test] Tweet sent');

  // ---------------------------------------
  // Example of dynamic GPT usage:
  // You can change the system prompt at runtime
  setTimeout(() => {
    console.log('[Test] Changing system prompt to a new persona...');
    sttTtsPlugin.setSystemPrompt(
      'You are a very sarcastic AI who uses short answers.',
    );
  }, 45_000);

  // Another example: after some time, switch to GPT-4
  setTimeout(() => {
    console.log('[Test] Switching GPT model to "gpt-4" (if available)...');
    sttTtsPlugin.setGptModel('gpt-4');
  }, 60_000);

  // Also, demonstrate how to manually call askChatGPT and speak the result
  setTimeout(async () => {
    console.log('[Test] Asking GPT for an introduction...');
    try {
      const response = await sttTtsPlugin['askChatGPT']('Introduce yourself');
      console.log('[Test] ChatGPT introduction =>', response);

      // Then speak it
      await sttTtsPlugin.speakText(response);
    } catch (err) {
      console.error('[Test] askChatGPT error =>', err);
    }
  }, 75_000);

  // Example: periodically speak a greeting every 60s
  setInterval(() => {
    sttTtsPlugin
      .speakText('Hello everyone, this is an automated greeting.')
      .catch((err) => console.error('[Test] speakText() =>', err));
  }, 20_000);

  // 4) Some event listeners
  space.on('speakerRequest', async (req) => {
    console.log('[Test] Speaker request =>', req);
    await space.approveSpeaker(req.userId, req.sessionUUID);

    // Remove the speaker after 60 seconds (testing only)
    setTimeout(() => {
      console.log(
        `[Test] Removing speaker => userId=${req.userId} (after 60s)`,
      );
      space.removeSpeaker(req.userId).catch((err) => {
        console.error('[Test] removeSpeaker error =>', err);
      });
    }, 60_000);
  });

  // When a user reacts, send back an emoji to test the flow
  space.on('guestReaction', (evt) => {
    // Pick a random emoji from the list
    const emojis = ['💯', '✨', '🙏', '🎮'];
    const emoji = emojis[Math.floor(Math.random() * emojis.length)];
    space.reactWithEmoji(emoji);
  });

  space.on('error', (err) => {
    console.error('[Test] Space Error =>', err);
  });

  // ==================================================
  // BEEP GENERATION (500 ms) @16kHz => 8000 samples
  // ==================================================
  const beepDurationMs = 500;
  const sampleRate = 16000;
  const totalSamples = (sampleRate * beepDurationMs) / 1000; // 8000
  const beepFull = new Int16Array(totalSamples);

  // Sine wave: 440Hz, amplitude ~12000
  const freq = 440;
  const amplitude = 12000;
  for (let i = 0; i < beepFull.length; i++) {
    const t = i / sampleRate;
    beepFull[i] = amplitude * Math.sin(2 * Math.PI * freq * t);
  }

  const FRAME_SIZE = 160;
  /**
   * Send a beep by slicing beepFull into frames of 160 samples
   */
  async function sendBeep() {
    console.log('[Test] Starting beep...');
    for (let offset = 0; offset < beepFull.length; offset += FRAME_SIZE) {
      const portion = beepFull.subarray(offset, offset + FRAME_SIZE);
      const frame = new Int16Array(FRAME_SIZE);
      frame.set(portion);
      space.pushAudio(frame, sampleRate);
      await new Promise((r) => setTimeout(r, 10));
    }
    console.log('[Test] Finished beep');
  }

  // Example: Send beep every 5s (currently commented out)
  // setInterval(() => {
  //   sendBeep().catch((err) => console.error('[Test] beep error =>', err));
  // }, 5000);

  console.log('[Test] Space is running... press Ctrl+C to exit.');

  // Graceful shutdown
  process.on('SIGINT', async () => {
    console.log('\n[Test] Caught interrupt signal, stopping...');
    await space.stop();
    console.log('[Test] Space stopped. Bye!');
    process.exit(0);
  });
}

main().catch((err) => {
  console.error('[Test] Unhandled main error =>', err);
  process.exit(1);
});
