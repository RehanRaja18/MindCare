import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_colors.dart';
import '../../models/program_data.dart';
import '../../providers/program_provider.dart';

int _durationToSeconds(String duration) {
  final parts = duration.split(':');
  if (parts.length != 2) return 60;
  final minutes = int.tryParse(parts[0]) ?? 0;
  final seconds = int.tryParse(parts[1]) ?? 0;
  return minutes * 60 + seconds;
}

class AudioPlayerScreen extends StatefulWidget {
  const AudioPlayerScreen({super.key, required this.track});
  final AudioTrack track;

  @override
  State<AudioPlayerScreen> createState() => _AudioPlayerScreenState();
}

class _AudioPlayerScreenState extends State<AudioPlayerScreen> {
  Timer? _timer;
  int _elapsed = 0;
  bool _isPlaying = true;
  late final int _totalSeconds;

  static const _barHeights = [
    10,
    18,
    26,
    14,
    22,
    30,
    18,
    12,
    24,
    16,
    28,
    10,
    20,
    15,
    26,
    18,
    9,
    22,
    14,
    19,
    27,
    13,
    21,
    16,
  ];

  @override
  void initState() {
    super.initState();
    _totalSeconds = _durationToSeconds(widget.track.duration);
    _startTimer();
  }

  void _startTimer() {
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!_isPlaying) return;
      setState(() {
        if (_elapsed >= _totalSeconds) {
          _isPlaying = false;
        } else {
          _elapsed++;
        }
      });
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  String _format(int seconds) {
    final m = (seconds ~/ 60).toString().padLeft(2, '0');
    final s = (seconds % 60).toString().padLeft(2, '0');
    return '$m:$s';
  }

  @override
  Widget build(BuildContext context) {
    final program = context.watch<ProgramProvider>();
    final bookmarked = program.isTrackBookmarked(widget.track.id);
    final progressRatio = _totalSeconds == 0 ? 0.0 : _elapsed / _totalSeconds;

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [AppColors.audioCardStart, Color(0xFF181C30)],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Column(
              children: [
                Row(
                  children: [
                    IconButton(
                      onPressed: () => Navigator.of(context).maybePop(),
                      icon: const Icon(Icons.expand_more, color: Colors.white),
                    ),
                    const Spacer(),
                    IconButton(
                      onPressed: () => context
                          .read<ProgramProvider>()
                          .toggleTrackBookmark(widget.track.id),
                      icon: Icon(
                        bookmarked ? Icons.bookmark : Icons.bookmark_border,
                        color: Colors.white,
                      ),
                    ),
                  ],
                ),
                const Spacer(),
                if (widget.track.tag.isNotEmpty) ...[
                  Text(
                    widget.track.tag,
                    style: const TextStyle(
                      color: Colors.white54,
                      letterSpacing: 1,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 10),
                ],
                Text(
                  widget.track.title,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 30,
                    fontFamily: 'serif',
                  ),
                ),
                const SizedBox(height: 20),
                if (widget.track.arabic != null) ...[
                  Text(
                    widget.track.arabic!,
                    textDirection: TextDirection.rtl,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 24,
                      height: 1.6,
                    ),
                  ),
                  const SizedBox(height: 14),
                ],
                if (widget.track.translation.isNotEmpty)
                  Text(
                    widget.track.translation,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      color: Colors.white60,
                      fontSize: 15,
                      fontStyle: FontStyle.italic,
                    ),
                  ),
                const Spacer(),
                SizedBox(
                  height: 44,
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: List.generate(_barHeights.length, (i) {
                      final played = (i / _barHeights.length) < progressRatio;
                      return Expanded(
                        child: Container(
                          margin: const EdgeInsets.symmetric(horizontal: 1.5),
                          height: _barHeights[i].toDouble(),
                          decoration: BoxDecoration(
                            color: played
                                ? Colors.white
                                : Colors.white.withOpacity(0.25),
                            borderRadius: BorderRadius.circular(2),
                          ),
                        ),
                      );
                    }),
                  ),
                ),
                const SizedBox(height: 10),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      _format(_elapsed),
                      style: const TextStyle(
                        color: Colors.white54,
                        fontSize: 12,
                      ),
                    ),
                    Text(
                      widget.track.duration,
                      style: const TextStyle(
                        color: Colors.white54,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 30),
                GestureDetector(
                  onTap: () => setState(() => _isPlaying = !_isPlaying),
                  child: Container(
                    width: 72,
                    height: 72,
                    decoration: const BoxDecoration(
                      color: Colors.white,
                      shape: BoxShape.circle,
                    ),
                    child: Icon(
                      _isPlaying ? Icons.pause : Icons.play_arrow,
                      color: AppColors.audioCardEnd,
                      size: 32,
                    ),
                  ),
                ),
                const SizedBox(height: 40),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
