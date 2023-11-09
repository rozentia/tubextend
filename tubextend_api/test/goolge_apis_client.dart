import 'package:googleapis_auth/auth_io.dart';
import 'package:http/http.dart' as http;
import 'package:tubextend_api/src/core/constants.dart';
import 'package:tubextend_api/src/core/logger.dart';

import 'env.dart';

Future<AuthClient> getAuthClient() async {
  final client = http.Client();

  try {
    final credentials = await obtainAccessCredentialsViaUserConsent(
      ClientId(
        Env.googleClientId,
        Env.googleClientSecret,
      ),
      kTubeXtendGoogleApisScopes,
      client,
      (String url) => logger.i('Please go to the following URL and grant access:\n$url'),
    );
    return authenticatedClient(client, credentials);
  } catch (e) {
    logger.e(e);
    rethrow;
  }
}
