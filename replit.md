# Overview

Health Saksham (स्वास्थ्य मित्र) is a bilingual public health chatbot application designed to provide health information and assistance in both Hindi and English. The application serves as a personal health assistant, offering information about disease symptoms, vaccination schedules, preventive care, and health alerts. Built with Flask as the backend framework, it integrates OpenAI's API for intelligent conversational responses and uses SQLite for local data storage.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Backend Architecture
The application uses Flask as the web framework with a class-based design pattern centered around the `HealthChatbot` class. The backend handles HTTP requests through RESTful endpoints, processes multilingual input using language detection, and integrates with OpenAI's API for generating contextual health responses. CORS is enabled for cross-origin requests, and custom headers are set for cache control in the Replit environment.

## Frontend Architecture
The frontend is built with Bootstrap 5 for responsive design and uses vanilla JavaScript for chat functionality. The interface is designed as a single-page application with a chat container, message input area, and quick action buttons. The design supports both Hindi and English languages with appropriate typography and cultural considerations.

## Data Storage
SQLite is used as the primary database solution with two main tables:
- `vaccination_schedule`: Stores vaccine information with multilingual descriptions
- `outbreak_alerts`: Manages health alerts and outbreak information
The database initialization occurs at application startup through the `HealthChatbot` class constructor.

## Language Processing
The system uses the `langdetect` library to automatically detect user input language (Hindi or English) and provides appropriate responses. Error handling is implemented for cases where language detection fails.

## AI Integration
OpenAI's API is integrated to provide intelligent, contextual responses to health-related queries. The system maintains conversation context and can provide specialized health information based on user questions.

# External Dependencies

## AI Services
- **OpenAI API**: Primary AI service for generating intelligent health responses and maintaining conversational context

## Frontend Libraries
- **Bootstrap 5**: CSS framework for responsive UI components
- **Font Awesome 6**: Icon library for UI elements

## Python Libraries
- **Flask**: Web application framework
- **Flask-CORS**: Cross-origin resource sharing support
- **langdetect**: Automatic language detection for multilingual support
- **openai**: Official OpenAI Python SDK for API integration

## Database
- **SQLite3**: Local database for storing vaccination schedules and health alerts (built into Python standard library)

## Environment Variables
- **OPENAI_API_KEY**: Required for OpenAI API authentication
