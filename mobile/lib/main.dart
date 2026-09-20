import 'package:flutter/material.dart';
import 'features/auth/login_screen.dart';

void main() {
  runApp(const SortmaticApp());
}

class SortmaticApp extends StatelessWidget {
  const SortmaticApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SORT-MATIC Mobile',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        primarySwatch: Colors.cyan,
        scaffoldBackgroundColor: const Color(0xFF0F172A),
        fontFamily: 'Roboto',
      ),
      home: const LoginScreen(),
    );
  }
}
