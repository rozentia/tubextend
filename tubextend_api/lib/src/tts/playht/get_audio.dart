/*
import 'dart:convert';
import 'dart:io';
import 'package:eventsource/eventsource.dart';
import 'package:http/http.dart';

import '../../core/endpoints.dart';

enum PlayHTQuality {
  draft,
  low,
  medium,
  high,
  premium,
}

/// Creates an audio file from the given [text] using the ElevenLabs API.
///
/// The [apiKey] is required to access the API.
/// The [userId] is required to access the API.
/// The [voiceId] parameter specifies the voice to use for the speech.
/// The [fileName] parameter is optional and checks if the file exists by name and then calls it from cache, instead from the API.
/// The resulting file is stored in the [tempDirectory] directory.
/// The [stability] parameter ranges from 0.0 to 1.0 and determines the stability of the generated audio.
/// The [similarityBoost] parameter ranges from 0.0 to 1.0 and determines the similarity of the generated audio to the input text.
///
/// Returns a [File] object containing the generated audio.
Future<File> generateSpeechFrom({
  required String apiKey,
  required String userId,
  required String text,
  String voice = 's3://voice-cloning-zero-shot/d9ff78ba-d016-47f6-b0ef-dd630f59414e/female-cs/manifest.json',
  String? fileName,
  PlayHTQuality quality = PlayHTQuality.draft,
  required Directory tempDirectory,
  double stability = 0.0,
  double similarityBoost = 0.0,
}) async {
  // Converts text to speech

  Map<String, String> headers = {
    'AUTHORIZATION': apiKey,
    'X-USER-ID': userId,
    'accept': 'text/event-stream',
    'Content-Type': 'application/json',
  };

  Map<String, dynamic> jsonData = {
    'text': text,
    'voice': voice,
    'quality': quality.toString().split('.').last,
    'output_format': 'mp3',
    'voice_engine': 'PlayHT2.0',
  };

  try {
    final dir = tempDirectory;
    final file = File('${dir.path}/${fileName?.replaceAll(RegExp(r"\s+"), "")}.mp3');

    if (await file.exists()) return file;

    final client = Client();

    final eventSource = await EventSource.connect(
      Uri.parse(PlayHTEndpoints.generate),
      // client: client,
      headers: headers,
      body: json.encode(jsonData),
      method: 'POST',
    );
    print('connected to event source');
    final fileUrl = await waitForJobToFinishAndGetResultUrl(eventSource);
    final response = await client.get(Uri.parse(fileUrl));
    final bytes = response.bodyBytes;

    String id = DateTime.now().millisecondsSinceEpoch.toString();
    final newFile = fileName?.replaceAll(RegExp(r"\s+"), "") != null
        ? File('${dir.path}/${fileName?.replaceAll(RegExp(r"\s+"), "")}.mp3')
        : File('${dir.path}/$id.mp3');

    await newFile.writeAsBytes(bytes);
    return newFile;
  } catch (e) {
    rethrow;
  }
}

Future<String> waitForJobToFinishAndGetResultUrl(EventSource source) async {
  print('initializing stream');
  final Stream<Event> stream = source.asBroadcastStream();
  String? resultUrl;
  await for (var event in stream) {
    if (event.data == null) continue;
    print(event.data);
    final data = jsonDecode(event.data!);
    if (data['stage'] == 'complete' && data['url'] != null) {
      if (event.data == null) throw Exception('No data in final event');
      resultUrl = data['url'];
      break;
    }
  }
  if (resultUrl != null) {
    return resultUrl;
  } else {
    throw Exception('No result url');
  }
}
*/