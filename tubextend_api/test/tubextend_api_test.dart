import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:googleapis_auth/auth_io.dart';
import 'package:tubextend_api/src/core/logger.dart';
import 'package:tubextend_api/src/yt.dart';
import '../lib/src/core/extensions.dart';

import 'package:tubextend_api/tubextend_api.dart';

import 'env.dart';
import 'goolge_apis_client.dart';
import 'test_data.dart';

void main() {
  test('fetch a closed caption text', () async {
    final text = await getVideoTranscript('https://www.youtube.com/watch?v=n2grW7Knt1Y&t=512');
    expect(text?.isNotEmpty, true);
  });

  test('get s list of models', () async {
    final models = await getModels(Env.openAIKey);
    logger.i(models);
    expect(models.isNotEmpty, true);
  });

  test('get summary of text', () async {
    final summary = await getSummaryOf(someText, Env.openAIKey);
    logger.i(summary);
    expect(summary.isNotEmpty, true);
  });

  group('extensions', () {
    test('get a null free list', () {
      final testList = ['1', '2', '3', '4', '5', '6', '7', '8', '9', null];
      final testLength = testList.length;
      final nullFreeList = testList.nullFree;
      expect(nullFreeList.length, testLength - 1);
    });
    test('get uniques from list', () {
      final testList = ['1', '1', '1', null, null];
      final uniques = testList.uniques;
      expect(uniques.length, 2);
    });
    test('get a null free list of unique values', () {
      final testList = ['1', '2', '3', '4', '5', '5', '7', '8', '9', null];
      final testLength = testList.length;
      final nullFreeList = testList.uniquesNullFree;
      expect(nullFreeList.length, testLength - 2);
    });
  });

  group('ElevenLabs TTS', () {
    test('gets a list of voices', () async {
      final voices = await listVoices(Env.elevenLabsKey);
      expect(voices.isNotEmpty, true);
    });

    test('get audio from text', () async {
      final audio = await generateSpeechFrom(
        apiKey: Env.elevenLabsKey,
        text: someShortText,
        fileName: 'eleven_labs_audio_test',
        tempDirectory: Directory('./temp'),
        voiceId: elevenLabsDaveVoiceId,
      );
      expect(audio.existsSync(), true);
    });
  });

  group('Youtube Functions', () {
    late final AuthClient client;
    setUpAll(() async => client = await getAuthClient());

    test('get a list of categories as channel ids', () async {
      final categories = await getYTCategoriesAsChannelIds(client);
      logger.i(categories);
      expect(categories.isNotEmpty, true);
    });

    test('get a list of categories', () async {
      final categories = await getYTCategories(client);
      logger.i(categories);
      expect(categories.isNotEmpty, true);
    });

    test('get a list of videos from a category', () async {
      final categories = await getYTCategories(client);
      final videos = await getYTpopularVideosFromCategory(client, categories.first.id!);
      logger.i(videos);
      expect(videos.isNotEmpty, true);
    });

    test('get user playlists', () async {
      final playlists = await getUserPlaylists(client);
      logger.i('retreived a total of ${playlists.length} playlists');
      expect(playlists.isNotEmpty, true);
    });

    test('get videos from playlist', () async {
      final videos = await getVideosOfPlaylists(client, testPlaylistId);
      logger.i('retreived a total of ${videos.length} videos');
      expect(videos.isNotEmpty, true);
    });
  });
}
