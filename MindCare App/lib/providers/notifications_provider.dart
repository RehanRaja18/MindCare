import 'package:flutter/material.dart';
import '../models/notification_data.dart';

class NotificationsProvider extends ChangeNotifier {
  // Empty until the backend sends real notifications.
  List<NotificationItem> _items = [];

  void setItems(List<NotificationItem> items) {
    _items = items;
    notifyListeners();
  }


  List<NotificationItem> get todayItems => _items.where((n) => n.isToday).toList();
  List<NotificationItem> get earlierItems => _items.where((n) => !n.isToday).toList();
  int get unreadCount => _items.where((n) => !n.isRead).length;

  void markAllRead() {
    _items = _items.map((n) => n.copyWith(isRead: true)).toList();
    notifyListeners();
  }

  void markRead(String id) {
    final index = _items.indexWhere((n) => n.id == id);
    if (index == -1 || _items[index].isRead) return;
    final updated = List<NotificationItem>.from(_items);
    updated[index] = updated[index].copyWith(isRead: true);
    _items = updated;
    notifyListeners();
  }
}