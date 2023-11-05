import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:tubextend_api/src/core/endpoints.dart';
import 'package:tubextend_api/src/tts/elevenlabs/models.dart';

import '../../core/logger.dart';

/// Fetches a list of available voices from the ElevenLabs TTS API using the provided API key.
/// Returns a Future that completes with a List of Voice objects.
/// Throws an error if the API request fails
Future<List<Voice>> listVoices(String apiKey) async {
  try {
    final client = http.Client();
    final response = await client.get(
      Uri.parse(ElevenLabsEndpoints.voicesUrl),
      headers: {
        'xi-api-key': apiKey,
        'Content-Type': 'application/json',
      },
    );
    final json = jsonDecode(response.body);
    if (json['detail'] != null) throw Exception(response.body);
    if (json["voices"] == null) throw Exception('voices is null…\n${response.body}');
    final list = json["voices"] as List;
    List<Voice> voices = list.map((e) => Voice.fromJson(e)).toList();
    client.close();
    logger.i('Voices fetched successfully');
    return voices;
  } catch (e) {
    logger.e(e);
    rethrow;
  }
}
