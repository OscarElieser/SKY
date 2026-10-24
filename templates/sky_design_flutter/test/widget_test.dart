import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sky_design_flutter/main.dart';

void main() {
  testWidgets('Futuristic Flutter starter has CTA and working dialog', (tester) async {
    await tester.pumpWidget(const SkyDesignApp());
    await tester.pumpAndSettle();
    expect(find.text('SKY Studio'), findsWidgets);
    await tester.tap(find.text('Comenzar'));
    await tester.pumpAndSettle();
    expect(find.byType(AlertDialog), findsOneWidget);
    await tester.tap(find.text('Entendido'));
    await tester.pumpAndSettle();
    expect(find.byType(AlertDialog), findsNothing);
  });

  testWidgets('Search filters card content', (tester) async {
    await tester.pumpWidget(const SkyDesignApp());
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'no-existe-esta-capacidad');
    await tester.pumpAndSettle();
    expect(find.text('No hay resultados; probá con otra búsqueda.'), findsOneWidget);
  });
}
