library tubextend_api;

import 'package:googleapis/youtube/v3.dart';
import 'package:http/http.dart';

export './src/transcription.dart';
export './src/summary.dart';
export './src/tts/elevenlabs/get_audio.dart';
export './src/tts/elevenlabs/get_voices.dart';
export './src/tts/elevenlabs/models.dart';

final yt = YouTubeApi(Client());
