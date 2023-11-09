extension ExtendedList on List<String?> {
  /// Returns a new list containing all non-null elements of this list.
  List<String> get nullFree => List<String>.from(where((e) => e != null));

  /// Returns a list of unique non-null elements from the original list.
  List<String> get uniquesNullFree => toSet().toList().nullFree;

  /// Returns a list of unique strings including null if present (for null free uniques use [uniquesNullFree]).
  List<String?> get uniques => toSet().toList();
}
