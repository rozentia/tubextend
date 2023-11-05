class VoicesModel {
  VoicesModel({
    required this.voices,
  });

  List<Voice> voices;

  factory VoicesModel.fromJson(Map<String, dynamic> json) => VoicesModel(
        voices: List<Voice>.from(json["voices"].map((x) => Voice.fromJson(x))),
      );
}

class Voice {
  Voice({
    required this.voiceId,
    required this.name,
    required this.samples,
    required this.category,
    required this.language,
    required this.highQualityBaseModelIds,
    this.description,
    this.labels,
    this.previewUrl,
    required this.availableForTiers,
    this.settings,
  });

  final String voiceId;
  final String name;
  final List<Sample> samples;
  final String category;
  final String language;
  final String? description;
  final Map<String, dynamic>? labels;
  final String? previewUrl;
  final List<dynamic> availableForTiers;
  final Settings? settings;
  final List<String> highQualityBaseModelIds;

  factory Voice.fromJson(Map<String, dynamic> json) => Voice(
        voiceId: json["voice_id"],
        name: json["name"],
        description: json['description'],
        language: json['fine_tuning']?['language'] ?? '??',
        highQualityBaseModelIds:
            (json['high_quality_base_model_ids'] is List ? json['high_quality_base_model_ids'] as List<dynamic> : [])
                .map<String>((e) => '$e')
                .toList(),
        samples: List<Sample>.from((json["samples"] ?? []).map((x) => Sample.fromJson(x))),
        category: json["category"],
        labels: json["labels"],
        previewUrl: json["preview_url"],
        availableForTiers: List<dynamic>.from((json["available_for_tiers"] ?? []).map((x) => x)),
        settings: Settings.fromJson(json["settings"]),
      );
}

class Settings {
  final double? stability;
  final double? similarityBoost;
  final double? style;
  final double? useSpeakerBoost;

  Settings({
    this.stability,
    this.similarityBoost,
    this.style,
    this.useSpeakerBoost,
  });

  factory Settings.fromJson(Map<String, dynamic>? json) => json == null
      ? Settings()
      : Settings(
          stability: json["stability"],
          similarityBoost: json["similarity_boost"],
          style: json["style"],
          useSpeakerBoost: json["use_speaker_boost"],
        );
}

class Sample {
  Sample({
    this.sampleId,
    this.fileName,
    this.mimeType,
    this.sizeBytes,
    this.hash,
  });

  String? sampleId;
  String? fileName;
  String? mimeType;
  int? sizeBytes;
  String? hash;

  factory Sample.fromJson(Map<String, dynamic>? json) => json == null
      ? Sample()
      : Sample(
          sampleId: json["sample_id"],
          fileName: json["file_name"],
          mimeType: json["mime_type"],
          sizeBytes: json["size_bytes"],
          hash: json["hash"],
        );
}
