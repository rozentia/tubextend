import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart';

import '../../core/endpoints.dart';
import '../../core/logger.dart';

/// Creates an audio file from the given [text] using the ElevenLabs API.
///
/// The [apiKey] is required to access the API.
/// The [voiceId] parameter specifies the voice to use for the speech. See https://api.elevenlabs.io/v1/voices for more info.
/// The [fileName] parameter is optional and checks if the file exists by name and then calls it from cache, instead from the API.
/// The resulting file is stored in the [tempDirectory] directory.
/// The [stability] parameter ranges from 0.0 to 1.0 and determines the stability of the generated audio.
/// The [similarityBoost] parameter ranges from 0.0 to 1.0 and determines the similarity of the generated audio to the input text.
///
/// Returns a [File] object containing the generated audio.
Future<File> generateSpeechFrom({
  required String apiKey,
  required String text,
  String voiceId = 'MF3mGyEYCl7XYWbV9V6O',
  String? fileName,
  required Directory tempDirectory,
  double stability = 0.0,
  double similarityBoost = 0.0,
}) async {
  // Converts text to speech
  var endpoint = 'text-to-speech/$voiceId';

  Map<String, String> headers = {
    'accept': 'audio/mpeg',
    'xi-api-key': apiKey,
    'Content-Type': 'application/json',
  };

  Map<String, dynamic> jsonData = {
    'text': text,
    'stability': stability,
    'similarity_boost': similarityBoost,
  };

  try {
    final dir = tempDirectory;
    final file = File('${dir.path}/${fileName?.replaceAll(RegExp(r"\s+"), "")}.mp3');

    if (await file.exists()) return file;

    final client = Client();

    var response = await client.post(
      Uri.parse("${ElevenLabsEndpoints.baseUrl}/$endpoint"),
      headers: headers,
      body: json.encode(jsonData),
    );
    String id = DateTime.now().millisecondsSinceEpoch.toString();

    final newFile = fileName?.replaceAll(RegExp(r"\s+"), "") != null
        ? File('${dir.path}/${fileName?.replaceAll(RegExp(r"\s+"), "")}.mp3')
        : File('${dir.path}/$id.mp3');

    final bytes = response.bodyBytes;
    await newFile.writeAsBytes(bytes);
    client.close();
    logger.i('Generated speech from text: $text \nin file: ${newFile.path}');
    return newFile;
  } catch (e) {
    logger.e(e);
    rethrow;
  }
}
