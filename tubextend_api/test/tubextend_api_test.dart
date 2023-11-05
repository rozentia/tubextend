import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:tubextend_api/src/core/logger.dart';

import 'package:tubextend_api/tubextend_api.dart';

import 'env.dart';
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
}
