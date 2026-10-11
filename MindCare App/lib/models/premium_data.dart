import 'package:flutter/material.dart';
import '../core/theme/app_colors.dart';

// ----- Journal -----

class JournalEntry {
  const JournalEntry({
    required this.id,
    required this.createdAt,
    required this.body,
    this.title,
    this.moodId,
    this.sharedWithTherapist = false,
  });

  final String id;
  final DateTime createdAt;
  final String? title;
  final String body;

  /// One of the daily mood ids ('bright', 'okay', 'wobbly', 'heavy', 'lost').
  final String? moodId;
  final bool sharedWithTherapist;

  JournalEntry copyWith({bool? sharedWithTherapist}) => JournalEntry(
        id: id,
        createdAt: createdAt,
        title: title,
        body: body,
        moodId: moodId,
        sharedWithTherapist: sharedWithTherapist ?? this.sharedWithTherapist,
      );
}

// ----- Outing activities -----

enum OutingType { walk, coffee, meal, hike }

extension OutingTypeInfo on OutingType {
  String get label => switch (this) {
        OutingType.walk => 'Walk',
        OutingType.coffee => 'Coffee',
        OutingType.meal => 'Meal',
        OutingType.hike => 'Hike',
      };

  IconData get icon => switch (this) {
        OutingType.walk => Icons.directions_walk,
        OutingType.coffee => Icons.local_cafe_outlined,
        OutingType.meal => Icons.restaurant_outlined,
        OutingType.hike => Icons.terrain,
      };

  Color get color => switch (this) {
        OutingType.walk => AppColors.programBreath,
        OutingType.coffee => AppColors.programBody,
        OutingType.meal => AppColors.programReflect,
        OutingType.hike => AppColors.progressActive,
      };
}

/// An outing a volunteer companion has offered. The companion is shown by
/// first name or alias only; contact details are never shared in the app.
class Outing {
  const Outing({
    required this.id,
    required this.type,
    required this.companionName,
    required this.area,
    required this.startsAt,
    required this.durationMinutes,
    this.note,
    this.companionRating,
  });

  final String id;
  final OutingType type;
  final String companionName;
  final String area; // a public meeting area, e.g. a park or café district
  final DateTime startsAt;
  final int durationMinutes;
  final String? note;
  final double? companionRating;
}

enum OutingStatus { requested, confirmed, completed, cancelled }

extension OutingStatusInfo on OutingStatus {
  String get label => switch (this) {
        OutingStatus.requested => 'Requested',
        OutingStatus.confirmed => 'Confirmed',
        OutingStatus.completed => 'Completed',
        OutingStatus.cancelled => 'Cancelled',
      };
}

/// The patient's own request to join an outing.
class OutingBooking {
  const OutingBooking({required this.outing, required this.status, this.rating, this.feedback});

  final Outing outing;
  final OutingStatus status;
  final int? rating; // 1-5, given after the outing
  final String? feedback;

  OutingBooking copyWith({OutingStatus? status, int? rating, String? feedback}) => OutingBooking(
        outing: outing,
        status: status ?? this.status,
        rating: rating ?? this.rating,
        feedback: feedback ?? this.feedback,
      );
}
