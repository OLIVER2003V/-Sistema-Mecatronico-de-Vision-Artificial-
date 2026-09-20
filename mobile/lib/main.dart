import 'package:flutter/material.dart';
import 'features/asistente/chat_screen.dart';

void main() {
  runApp(const SortmaticApp());
}

class SortmaticApp extends StatelessWidget {
  const SortmaticApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SORT-MATIC Assistant',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        primarySwatch: Colors.cyan,
        scaffoldBackgroundColor: const Color(0xFF12141C),
        fontFamily: 'Roboto',
      ),
      home: const ChatAsistenteScreen(),
    );
  }
}
