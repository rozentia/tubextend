// lib/env/env.dart
import 'package:envied/envied.dart';

part 'env.g.dart';

@Envied()
abstract class Env {
  @EnviedField(varName: 'OPENAI_KEY')
  static const String openAIKey = _Env.openAIKey;

  @EnviedField(varName: 'ELEVENLABS_KEY')
  static const String elevenLabsKey = _Env.elevenLabsKey;

  @EnviedField(varName: 'PLAYHT_USERID')
  static const String playHTUserId = _Env.playHTUserId;

  @EnviedField(varName: 'PLAYHT_SECRET_KEY')
  static const String playHTApiKey = _Env.playHTApiKey;

  @EnviedField(varName: 'GOOGLE_CLIENT_ID')
  static const String googleClientId = _Env.googleClientId;

  @EnviedField(varName: 'GOOGLE_CLIENT_SECRET')
  static const String googleClientSecret = _Env.googleClientSecret;
}
