# Agentic System Development Plan for TubeXtend

## **1. Overall Approach:**

- **Modular and Incremental:** We'll build the agentic system in a modular fashion, focusing on one agent at a time, ensuring each component is working correctly before moving on.
- **Test-Driven Development (TDD):** We'll write tests *before* implementing the core logic of each agent. This ensures each agent works as intended, even before it has a dependency to another part of the system.
- **Type Safety and Validation:** Leveraging Pydantic's strong typing and data validation to enforce data structure and reduce runtime errors.
- **Abstraction and Separation of Concerns:** Each agent will have a clear responsibility. We will abstract external services so changing any of the used providers or APIs won't affect the overall system.
- **Version Control:** Using Git for version control throughout the entire development process and branching strategies.
- **Code Review:** Implementing code reviews to ensure quality and compliance with the team's coding standards.

## **2. Development Environment Setup:**

- **Local Development Setup:** We will use local environment to test all the components, using docker to ensure consistency of the environment, and using local database and storage emulators.
- **Python Environment:** We will set up a virtual environment and use poetry or pipenv to manage dependencies.
- **IDE:** Use a suitable IDE like VSCode, PyCharm, or similar.
- **Supabase CLI:** Install and configure the Supabase CLI for local database and functions management.

## **3. Agent Development Workflow:**

For each agent, we will follow this detailed workflow:

1. **Define Agent's Responsibility:**
   - Clearly articulate the agent's specific task and boundaries.
   - Define what the agent receives as input and what it is expected to produce as output.
   - Identify any dependencies on other services or agents.
2. **Define Data Models (Pydantic):**
   - Create Pydantic models for the agent's input and output.
   - Ensure strong typing and clear validation rules.
   - Define all data dependencies using Pydantic models.
3. **Write Unit Tests (pytest):**
   - Write tests for the agent's core logic based on the Pydantic input/output models.
   - Use mocks for external services and database interaction.
   - Cover positive and negative scenarios, edge cases, and potential error conditions.
4. **Implement Agent Logic:**
   - Implement the agent's core logic based on the defined responsibility.
   - Use the specified external services, abstracted in a unified interface to ensure flexibility.
   - Use logging to track data flow and errors.
5. **Test Agent:**
   - Run unit tests and verify the agent's behavior.
   - Debug the agent if any tests fail.
6. **Document Agent:**
   - Add detailed comments to the agent's code.
   - Update any documentation required for the project.
7. **Integrate and Test:**
   - Add the created agent to the overall workflow and verify the correct data flow.
   - Make sure that all of the agents communicate to each other using the defined models.
8. **Refactor:** Refactor the code when necessary to improve readability and performance.

## **4. Agent-Specific Development Plan:**

Let's detail the implementation plan for each of the agents individually.

### **4.1. Channel Monitor Agent:**

- **Responsibility:**
  - Fetches channel and playlist information from the database.
  - Determines which channel collections to process daily based on a processing strategy.
  - Fetches new videos from specified channels and playlists using YouTube's API.
  - Stores new video metadata into the database.
- **Input:** Configuration settings, information from the database about channels, playlists, and previously processed content.
- **Output:** A list of new videos, organized by channel or playlist, along with their metadata.
- **Development Plan:**
  1. **Database Integration:** Set up the database models for Channels, Playlists and Videos and access to them.
  2. **Pydantic Models:** Define input and output models for the agent, as well as models for channels, playlists, videos.
  3. **YouTube API Wrapper:** Implement the YouTube API wrapper with functions for fetching new uploads.
  4. **Unit Tests:** Write tests for the agent's core logic, testing all the corner cases.
  5. **Implement Agent:** Implement the core logic for retrieving and storing the required information.
  6. **Test:** Test thoroughly all the cases, ensuring no corner case was omitted.

### **4.2. Content Retriever Agent:**

- **Responsibility:**
  - Takes a list of videos as input.
  - Downloads the audio from videos if no YouTube transcript is found.
  - Retrieves transcripts from YouTube if available, or transcribes using the configured STT provider.
  - Saves transcripts to the cloud storage.
  - Updates the database with transcript IDs and sources.
- **Input:** Video metadata and ids.
- **Output:** Transcripts associated with each video, and data about the source of each transcript.
- **Development Plan:**
  1. **Pydantic Models:** Define the data models for videos and transcripts.
  2. **YouTube API Integration:** Enhance the YouTube API Wrapper with functionality for retrieving transcript information.
  3. **STT API Wrappers:** Implement wrappers for the various STT providers, and configure them in the unified configuration.
  4. **Unit Tests:** Thoroughly test all the cases.
  5. **Implement Agent:** Implement the core logic for retrieving transcripts and storing the info in the database.
  6. **Test:** Ensure that the agent can fetch transcripts from YouTube and external STT providers.

### **4.3. Summarizer and Synthesizer Agent:**

- **Responsibility:**
  - Takes video transcripts and metadata as input.
  - Summarizes each transcript using a specified summarization model.
  - Synthesizes summaries into a single narrative, taking into account the context and relationships between videos.
- **Input:** Video metadata and transcripts.
- **Output:** A synthesized summary of multiple videos in a cohesive single narrative.
- **Development Plan:**
  1. **Pydantic Models:** Define input and output models for this agent.
  2. **Summarization Model Integration:** Implement an abstraction to any summarization model, and add configuration to choose the model.
  3. **Unit Tests:** Write unit tests for both summarization and synthesis, including different error cases.
  4. **Implement Agent:** Implement the core logic for summarizing transcripts and generating the final narrative.
  5. **Test:** Test all the functionalities and verify the logic is correct.

### **4.4. Script Generator Agent:**

- **Responsibility:**
  - Takes the synthesized narrative as input.
  - Structures the narrative into a conversational podcast script with a single speaker style.
  - Adds conversational cues for a pleasant listening experience.
- **Input:** Synthesized narrative.
- **Output:** A podcast script.
- **Development Plan:**
  2. **Pydantic Models:** Define input and output models for the agent.
  3. **Unit Tests:** Create tests that check for the proper structure of the generated script.
  4. **Implement Agent:** Implement the core logic for restructuring the narrative into a script.
  5. **Test:** Test all the logic and corner cases.

**4.5. Speech Synthesizer Agent:**

- **Responsibility:**
  - Takes the podcast script as input.
  - Converts the script to audio using a configured TTS service.
  - Saves the generated audio to the cloud storage.
- **Input:** Podcast script.
- **Output:** URL to the generated audio, metadata about the generated audio.
- **Development Plan:**
  1. **Pydantic Models:** Define the input and output models.
  2. **TTS API Wrappers:** Implement wrappers for the various TTS providers.
  3. **Unit Tests:** Add unit tests to test the functionality of the wrappers.
  4. **Implement Agent:** Implement the core logic to transform the script to audio using the TTS engine, also implement logic for saving in the cloud storage and the database.
  5. **Test:** Test all of the configurations and external providers to ensure everything works.

### **4.6. Output Manager Agent:**

- **Responsibility:**
  - Takes the URL of the audio podcast file as input.
  - Creates a podcast metadata record in the database.
  - Updates the video table in the database with the generated podcast ids.
- **Input:** Audio file URL, and metadata associated with the creation.
- **Output:** Update to the database.
- **Development Plan:**
  1. **Pydantic Models:** Define the input and output model of the agent.
  2. **Unit Tests:** Add tests to ensure the logic of this agent works correctly.
  3. **Implement Agent:** Implement the logic to save data in the database.
  4. **Test:** Run the tests and fix any possible issue.

## **5. Integration and Orchestration:**

- **Cloud Functions:**
  - Implement the main workflow in an orchestrating Supabase function.
  - Each Agent will be hosted as an independent edge function.
  - Use database data to feed the different agents as required.
  - Expose each agent with a specific API endpoint and the main workflow in another endpoint for orchestration.
- **Error Handling:** Implement error handling to deal with errors. Logging is key for debugging, and the function will log all errors and data as required to debug when the system has issues.

## **6. Deployment:**

- **Supabase:** Deploy each agent as individual functions.
- **Version Control:** Use proper version control to keep track of the changes made.

## **7. Iteration and Refinement:**

- **Monitoring:** Implement logging to monitor performance of the agent.
- **User Feedback:** Implement mechanisms to get user feedback and improve the quality of the generated podcasts.
