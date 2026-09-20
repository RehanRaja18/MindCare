import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_colors.dart';
import '../../providers/program_provider.dart';
import '../../widgets/motivation/audio_list_item.dart';
import 'audio_player_screen.dart';

class BookmarksScreen extends StatelessWidget {
  const BookmarksScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<ProgramProvider>();
    final tracks = provider.bookmarkedTracks;

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [AppColors.motivationBgStart, AppColors.motivationBgEnd],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Column(
              children: [
                Row(
                  children: [
                    IconButton(
                      onPressed: () => Navigator.of(context).maybePop(),
                      icon: const Icon(Icons.chevron_left, color: Colors.white),
                    ),
                    const Expanded(
                      child: Text(
                        'BOOKMARKS',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          letterSpacing: 1,
                          color: Colors.white70,
                          fontWeight: FontWeight.w600,
                          fontSize: 12,
                        ),
                      ),
                    ),
                    const SizedBox(width: 48),
                  ],
                ),
                const SizedBox(height: 10),
                Expanded(
                  child: tracks.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: const [
                              Icon(
                                Icons.bookmark_border,
                                size: 40,
                                color: Colors.white38,
                              ),
                              SizedBox(height: 14),
                              Text(
                                'Nothing saved yet.',
                                style: TextStyle(color: Colors.white70),
                              ),
                              SizedBox(height: 6),
                              Text(
                                'Tap the bookmark icon on any track to save it here.',
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  color: Colors.white38,
                                  fontSize: 12,
                                ),
                              ),
                            ],
                          ),
                        )
                      : ListView(
                          children: tracks
                              .map(
                                (track) => AudioListItem(
                                  track: track,
                                  isPlaying: provider.isPlaying(track.id),
                                  onTap: () => Navigator.of(context).push(
                                    MaterialPageRoute(
                                      builder: (_) =>
                                          AudioPlayerScreen(track: track),
                                    ),
                                  ),
                                ),
                              )
                              .toList(),
                        ),
                ),
                const SizedBox(height: 20),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
