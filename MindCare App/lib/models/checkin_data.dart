import 'package:flutter/material.dart';

enum MessageSender { user, assistant }

enum NervousSystemState { calm, activated }

class DailyMoodOption {
  const DailyMoodOption(this.id, this.label, this.color);
  final String id;
  final String label;
  final Color color;
}

/// One sample from the wearable sensors. Steps is the running total for the
/// day if the device reports it, otherwise null.
class VitalReading {
  const VitalReading({required this.at, required this.heartRate, required this.breathingRate, this.steps});

  final DateTime at;
  final int heartRate; // bpm
  final int breathingRate; // breaths per minute
  final int? steps;
}

/// What Pulse and Home display, derived from the recent [VitalReading]s.
class VitalsSnapshot {
  const VitalsSnapshot({
    required this.heartRate,
    required this.breathingRate,
    required this.steps,
    required this.heartTrend,
    required this.breathingTrend,
    required this.stepsTrend,
    required this.state,
  });

  final int heartRate;
  final int breathingRate;
  final int? steps;
  final List<double> heartTrend;
  final List<double> breathingTrend;
  final List<double> stepsTrend;
  final NervousSystemState state;

  String get stateLabel => state == NervousSystemState.calm ? 'Calm' : 'Activated';
}

class BreathingExercise {
  const BreathingExercise({
    required this.title,
    required this.subtitle,
    required this.ctaLabel,
  });

  final String title;
  final String subtitle;
  final String ctaLabel;
}

class ChatMessage {
  ChatMessage({
    required this.id,
    required this.sender,
    this.text,
    this.exercise,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  final String id;
  final MessageSender sender;
  final String? text;
  final BreathingExercise? exercise;
  final DateTime timestamp;
}

class ProgressInsight {
  const ProgressInsight({
    required this.icon,
    required this.iconBackground,
    required this.title,
    required this.description,
  });

  final IconData icon;
  final Color iconBackground;
  final String title;
  final String description;
}