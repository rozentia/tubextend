class PaginatedResponse<T> {
  final String? nextPageToken;
  final String? prefiousPageToken;
  final T data;

  PaginatedResponse({
    this.nextPageToken,
    this.prefiousPageToken,
    required this.data,
  });
}
