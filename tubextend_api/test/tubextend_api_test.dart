import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:tubextend_api/env.dart';
import 'package:tubextend_api/src/summary.dart';
import 'package:tubextend_api/src/tts/elevenlabs/get_audio.dart' as eleven;
import 'package:tubextend_api/src/tts/elevenlabs/get_voices.dart';
import 'package:tubextend_api/src/tts/playht/get_audio.dart' as playht;

import 'package:tubextend_api/tubextend_api.dart';

import 'test_data.dart';

void main() {
  test('fetch a closed caption text', () async {
    final text = await getVideoTranscript('https://www.youtube.com/watch?v=n2grW7Knt1Y&t=512');
    expect(text?.isNotEmpty, true);
  });

  test('get s list of models', () async {
    final models = await getModels(Env.openAIKey);
    print(models);
    expect(models.isNotEmpty, true);
  });

  test('get summary of text', () async {
    final summary = await getSummaryOf(someText, Env.openAIKey);
    print(summary);
    expect(summary.isNotEmpty, true);
  });

  group('ElevenLabs TTS', () {
    test('gets a list of voices', () async {
      final voices = await listVoices(Env.elevenLabsKey);
      expect(voices.isNotEmpty, true);
    });

    test('get audio from text', () async {
      final audio = await eleven.generateSpeechFrom(
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
