import 'package:dart_openai/dart_openai.dart';

import 'core/logger.dart';

/// Returns a summary of the given [text] in a conversational and casual tone using OpenAI's GPT-3.5-turbo model.
///
/// The [openAIAPIKey] is required to authenticate the API request.
/// Throws an [Exception] if no choices are found.
Future<String> getSummaryOf(String text, String openAIAPIKey) async {
  OpenAI.apiKey = openAIAPIKey;
  final openAI = OpenAI.instance;
  final prompt = 'summarize the key points of the following text in a conversational and casual tone: $text';
  try {
    final chatCompletion = await openAI.chat.create(
      model: 'gpt-3.5-turbo',
      // maxTokens: 64,
      temperature: 0.7,
      topP: 1,
      n: 1,
      frequencyPenalty: 0,
      presencePenalty: 0,
      messages: [
        OpenAIChatCompletionChoiceMessageModel(role: OpenAIChatMessageRole.user, content: prompt),
      ],
    );

    if (chatCompletion.haveChoices != true) throw Exception('No choices found');
    logger.i('Summary fetched successfully');
    return chatCompletion.choices.first.message.content;
  } catch (e) {
    logger.e(e);
    rethrow;
  }
}

/// Returns a string of all the available OpenAI models.
///
/// The function takes an [openAIAPIKey] as input and sets it as the API key for OpenAI.
/// It then retrieves a list of all the available models and returns their IDs as a string,
/// separated by newlines.
Future<String> getModels(String openAIAPIKey) async {
  OpenAI.apiKey = openAIAPIKey;
  final openAI = OpenAI.instance;
  try {
    final result = await openAI.model.list();
    logger.i('Models fetched successfully');
    return result.map((m) => m.id).join('\n');
  } catch (e) {
    logger.e(e);
    rethrow;
  }
}
