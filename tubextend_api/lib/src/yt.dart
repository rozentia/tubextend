import 'package:googleapis/youtube/v3.dart';
import 'package:http/http.dart';
import 'package:tubextend_api/src/core/logger.dart';
import 'package:tubextend_api/src/core/models.dart';
import './core/extensions.dart';

Future<List<String>> getYTCategoriesAsChannelIds(Client client, {String? hl, String regionCode = 'US'}) async {
  final ytApi = YouTubeApi(client);
  try {
    final categories = await ytApi.videoCategories.list(
      ['snippet'],
      hl: hl,
      regionCode: regionCode,
    );
    if (categories.items?.isNotEmpty != true) throw Exception('No categories found');
    return categories.items!.map<String?>((category) => category.snippet?.channelId).toList().uniquesNullFree;
  } catch (e) {
    logger.e(e);
    rethrow;
  }
}

Future<List<VideoCategory>> getYTCategories(Client client, {String? hl, String regionCode = 'US'}) async {
  final ytApi = YouTubeApi(client);
  try {
    final categories = await ytApi.videoCategories.list(
      ['snippet'],
      hl: hl,
      regionCode: regionCode,
    );
    if (categories.items?.isNotEmpty != true) throw Exception('No categories found');
    return categories.items!;
  } catch (e) {
    logger.e(e);
    rethrow;
  }
}

Future<List<Video>> getYTpopularVideosFromCategory(
  Client client,
  String categoryId, {
  String? hl,
  String regionCode = 'US',
}) async {
  final ytApi = YouTubeApi(client);
  try {
    final response = await ytApi.videos.list(
      ['snippet'],
      chart: 'mostPopular',
      videoCategoryId: categoryId,
      hl: hl,
      regionCode: regionCode,
      maxResults: 50,
    );

    if (response.items?.isNotEmpty != true) throw Exception('No videos found');
    return response.items!;
  } catch (e) {
    logger.e(e);
    rethrow;
  }
}

Future<List<Video>> searchForVideosByString(Client client, String query) async {
  final ytApi = YouTubeApi(client);
  try {
    final response = await ytApi.search.list(
      ['snippet'],
      q: query,
      type: ['video'],
    );
    if (response.items?.isNotEmpty != true) throw Exception('No videos found');
    return response.items!
        .map<Video?>((e) => e.id?.videoId == null
            ? null
            : Video(
                snippet: VideoSnippet(
                  title: e.snippet?.title,
                  description: e.snippet?.description,
                  thumbnails: e.snippet?.thumbnails,
                  publishedAt: e.snippet?.publishedAt,
                  channelId: e.snippet?.channelId,
                  channelTitle: e.snippet?.channelTitle,
                ),
                id: e.id!.videoId!,
              ))
        .where((e) => e != null)
        .toList()
        .cast<Video>();
  } catch (e) {
    logger.e(e);
    rethrow;
  }
}

Future<List<Subscription>> getUserSubscriptions(Client client) async {
  final ytApi = YouTubeApi(client);
  try {
    final List<Subscription> subscriptions = [];
    String? nextPageToken = '_';
    while (nextPageToken != null) {
      final response = await ytApi.subscriptions.list(
        ['snippet', 'contentDetails'],
        mine: true,
        maxResults: 50,
        pageToken: nextPageToken == '_' ? null : nextPageToken,
      );
      if (response.items?.isNotEmpty != true) throw Exception('No subscriptions found');
      subscriptions.addAll(response.items!);
      nextPageToken = response.nextPageToken;
    }
    return subscriptions;
  } catch (e) {
    logger.e(e);
    rethrow;
  }
}

Future<List<Playlist>> getUserPlaylists(Client client) async {
  final ytApi = YouTubeApi(client);
  try {
    final List<Playlist> playlists = [];
    String? nextPageToken = '_';
    while (nextPageToken != null) {
      final response = await ytApi.playlists.list(
        ['snippet', 'contentDetails'],
        maxResults: 50,
        mine: true,
        pageToken: nextPageToken == '_' ? null : nextPageToken,
      );
      if (response.items?.isNotEmpty != true) throw Exception('No playlists found');
      playlists.addAll(response.items!);
      nextPageToken = response.nextPageToken;
    }
    return playlists;
  } catch (e) {
    logger.e(e);
    rethrow;
  }
}

Future<String> getUploadsPlaylistIdFromSubscription(Client client, Subscription subscription) async {
  final subscriptionChannelId = subscription.snippet?.resourceId?.channelId;
  if (subscriptionChannelId == null) throw Exception('No channel id found');
  try {
    final ytApi = YouTubeApi(client);
    final response = await ytApi.channels.list(
      ['contentDetails'],
      id: [subscriptionChannelId],
    );
    final uploadsPlaylistId = response.items?.first.contentDetails?.relatedPlaylists?.uploads;
    if (uploadsPlaylistId == null) throw Exception('No uploads playlist found');
    return uploadsPlaylistId;
  } catch (e) {
    logger.e(e);
    rethrow;
  }
}

Future<List<Video>> getAllVideosOfPlaylists(Client client, String playlistId) async {
  if (playlistId.isEmpty) throw Exception('Playlist id cannot be empty');
  final ytApi = YouTubeApi(client);
  try {
    final List<PlaylistItem> playlistItems = [];
    String? nextPageToken = '_';
    while (nextPageToken != null) {
      final response = await ytApi.playlistItems.list(
        playlistId: playlistId,
        ['snippet'],
        maxResults: 50,
        pageToken: nextPageToken == '_' ? null : nextPageToken,
      );
      if (response.items?.isNotEmpty != true) throw Exception('No playlists found');
      playlistItems.addAll(response.items!);
      nextPageToken = response.nextPageToken;
    }
    return playlistItems.map<Video?>((e) => e.video).where((e) => e != null).toList().cast<Video>();
  } catch (e) {
    logger.e(e);
    rethrow;
  }
}

Future<List<Video>> getnVideosFromPlaylist(Client client, String playlistId, {int maxResults = 50}) async {
  final ytApi = YouTubeApi(client);
  try {
    final playlistItems = await ytApi.playlistItems.list(
      ['snippet', 'contentDetails'],
      playlistId: playlistId,
      maxResults: maxResults,
    );
    if (playlistItems.items?.isNotEmpty != true) throw Exception('No videos found');
    return playlistItems.items!.map((e) => e.video).where((e) => e != null).toList().cast<Video>();
  } catch (e) {
    logger.e(e);
    rethrow;
  }
}

Future<PaginatedResponse<List<Video>>> getPaginatedVideosFromPlaylist(
  Client client,
  String playlistId, {
  int? maxResults = 50,
  String? pageToken,
}) async {
  final ytApi = YouTubeApi(client);
  try {
    final response = await ytApi.playlistItems.list(
      ['snippet', 'contentDetails'],
      playlistId: playlistId,
      maxResults: maxResults,
      pageToken: pageToken,
    );
    logger.i(
        'nextPageToken: ${response.nextPageToken}\nkind: ${response.kind}\npageInfo:\n\ttotal: ${response.pageInfo?.totalResults}\n\tper page: ${response.pageInfo?.resultsPerPage}');
    if (response.items?.isNotEmpty != true) throw Exception('No videos found');
    return PaginatedResponse(
      nextPageToken: response.nextPageToken,
      prefiousPageToken: response.prevPageToken,
      data: response.items!.map((e) => e.video).where((e) => e != null).toList().cast<Video>(),
    );
  } catch (e) {
    logger.e(e);
    rethrow;
  }
}

extension PlaylistItemExtension on PlaylistItem {
  Video? get video => snippet?.resourceId?.videoId == null
      ? null
      : Video(
          snippet: VideoSnippet(
            title: snippet!.title,
            description: snippet!.description,
            thumbnails: snippet!.thumbnails,
            publishedAt: snippet!.publishedAt,
            channelId: snippet!.channelId,
            channelTitle: snippet!.channelTitle,
          ),
          id: snippet!.resourceId!.videoId!,
        );
}
