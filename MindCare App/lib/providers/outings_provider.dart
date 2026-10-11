import 'package:flutter/material.dart';
import '../models/premium_data.dart';

/// Outing activities (a Premium feature): walks, coffee, meals and hikes
/// with a volunteer companion, to ease loneliness.
///
/// Starts empty. Outings offered by companions come from the backend
/// ([setAvailable]); the patient's own requests are tracked in [bookings].
class OutingsProvider extends ChangeNotifier {
  final List<Outing> _available = [];
  final List<OutingBooking> _bookings = [];

  OutingType? filter;

  List<Outing> get available {
    final now = DateTime.now();
    final booked = _bookings.map((b) => b.outing.id).toSet();
    return _available
        .where((o) => o.startsAt.isAfter(now) && !booked.contains(o.id) && (filter == null || o.type == filter))
        .toList()
      ..sort((a, b) => a.startsAt.compareTo(b.startsAt));
  }

  /// Most recent first.
  List<OutingBooking> get bookings => List.unmodifiable(_bookings);

  void setFilter(OutingType? type) {
    filter = filter == type ? null : type;
    notifyListeners();
  }

  void setAvailable(List<Outing> outings) {
    _available
      ..clear()
      ..addAll(outings);
    notifyListeners();
  }

  void setBookings(List<OutingBooking> bookings) {
    _bookings
      ..clear()
      ..addAll(bookings);
    notifyListeners();
  }

  OutingBooking? bookingFor(String outingId) {
    for (final b in _bookings) {
      if (b.outing.id == outingId) return b;
    }
    return null;
  }

  void requestOuting(Outing outing) {
    if (bookingFor(outing.id) != null) return;
    _bookings.insert(0, OutingBooking(outing: outing, status: OutingStatus.requested));
    notifyListeners();
  }

  void cancelRequest(String outingId) => _update(outingId, (b) => b.copyWith(status: OutingStatus.cancelled));

  void rate(String outingId, int rating, {String? feedback}) =>
      _update(outingId, (b) => b.copyWith(rating: rating.clamp(1, 5), feedback: feedback));

  void _update(String outingId, OutingBooking Function(OutingBooking) change) {
    final i = _bookings.indexWhere((b) => b.outing.id == outingId);
    if (i == -1) return;
    _bookings[i] = change(_bookings[i]);
    notifyListeners();
  }
}
