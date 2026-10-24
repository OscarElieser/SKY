import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'sky_config.dart';

void main() => runApp(const SkyDesignApp());

class SkyDesignApp extends StatelessWidget {
  const SkyDesignApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: skyTitle,
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(skyColorPrimary),
          brightness: Brightness.dark,
        ),
      ),
      home: const SkyHome(),
    );
  }
}

class SkyHome extends StatefulWidget {
  const SkyHome({super.key});
  @override
  State<SkyHome> createState() => _SkyHomeState();
}

class _SkyHomeState extends State<SkyHome> {
  final ScrollController _scroll = ScrollController();
  String query = '';

  @override
  void dispose() {
    _scroll.dispose();
    super.dispose();
  }
  final features = const [
    (Icons.auto_awesome, skyFeatureOne, 'Una interfaz con identidad y jerarquía.'),
    (Icons.animation, skyFeatureTwo, 'Animaciones que acompañan la navegación.'),
    (Icons.verified_user_outlined, skyFeatureThree, 'Contraste y controles accesibles.'),
  ];

  void details(String title, String message) {
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Entendido'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final wide = width >= 760;
    final primary = const Color(skyColorPrimary);
    final reduced = MediaQuery.disableAnimationsOf(context);
    final visible = features.where((item) => (item.$2 + ' ' + item.$3)
        .toLowerCase().contains(query.toLowerCase())).toList();

    Widget animate(Widget child, int delay) {
      if (reduced) return child;
      return child.animate(delay: Duration(milliseconds: delay))
        .fadeIn(duration: 400.ms)
        .slideY(begin: .08, end: 0, duration: 400.ms);
    }

    return Scaffold(
      appBar: AppBar(
        backgroundColor: const Color(0xFF071119),
        title: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(Icons.auto_awesome, color: primary),
          const SizedBox(width: 8),
          Flexible(child: Text(skyTitle, maxLines: 1,
              overflow: TextOverflow.ellipsis)),
        ]),
        actions: [
          IconButton(
            tooltip: 'Información',
            onPressed: () => details('SKY Design Studio',
              'Esta plantilla demuestra diseño responsivo y animación real.'),
            icon: const Icon(Icons.info_outline)),
        ],
      ),
      body: Container(
        decoration: const BoxDecoration(gradient: LinearGradient(
          colors: [Color(0xFF071119), Color(0xFF181A34)],
          begin: Alignment.topLeft, end: Alignment.bottomRight)),
        child: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1060),
              child: ListView(
                controller: _scroll,
                padding: EdgeInsets.symmetric(
                  horizontal: wide ? 35 : 20, vertical: 26),
                children: [
                  animate(Text('SKY  /  EXPERIENCIA INMERSIVA',
                    style: TextStyle(
                      fontSize: 11, letterSpacing: 2.1, color: primary)), 0),
                  const SizedBox(height: 18),
                  animate(Text(skySubtitle, style: TextStyle(
                    fontSize: wide ? 60 : 38, height: 1.1,
                    fontWeight: FontWeight.bold, letterSpacing: -1.7)), 80),
                  const SizedBox(height: 15),
                  animate(const Text(skyDescription,
                    style: TextStyle(fontSize: 16, height: 1.7,
                      color: Color(0xFFB6CBD5))), 110),
                  const SizedBox(height: 23),
                  animate(Wrap(spacing: 11, runSpacing: 10, children: [
                    FilledButton.icon(
                      onPressed: () => details('Comenzar',
                        'Plantilla de demostración. Vinculá aquí tu servicio real con autorización.'),
                      icon: const Icon(Icons.arrow_outward),
                      label: const Text('Comenzar')),
                    OutlinedButton.icon(
                      onPressed: () {
                        if (!_scroll.hasClients) return;
                        _scroll.animateTo(
                          _scroll.position.maxScrollExtent,
                          duration: const Duration(milliseconds: 400),
                          curve: Curves.easeOutCubic,
                        );
                      },
                      icon: const Icon(Icons.explore_outlined),
                      label: const Text('Explorar')),
                  ]), 150),
                  const SizedBox(height: 30),
                  animate(Container(
                    height: 208,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(26),
                      border: Border.all(color: primary.withValues(alpha: .35)),
                      gradient: const LinearGradient(colors: [
                        Color(0x663BABB0), Color(0x558A75DF)
                      ])),
                    child: Center(child: Icon(Icons.auto_awesome,
                      size: 86, color: primary)),
                  ), 190),
                  const SizedBox(height: 35),
                  const Text('Capacidades', style: TextStyle(
                    fontSize: 26, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 17),
                  TextField(
                    onChanged: (value) => setState(() => query = value),
                    decoration: InputDecoration(
                      prefixIcon: const Icon(Icons.search),
                      labelText: 'Buscar capacidades',
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(15)),
                    ),
                  ),
                  const SizedBox(height: 20),
                  if (visible.isEmpty)
                    const Padding(
                      padding: EdgeInsets.all(18),
                      child: Text('No hay resultados; probá con otra búsqueda.')),
                  LayoutBuilder(builder: (context, box) {
                    final cols = box.maxWidth > 750 ? 3 :
                      box.maxWidth > 470 ? 2 : 1;
                    return GridView.builder(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: visible.length,
                      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: cols, mainAxisSpacing: 13,
                        crossAxisSpacing: 13, mainAxisExtent: 220),
                      itemBuilder: (context, index) {
                        final item = visible[index];
                        return animate(Card(
                          color: const Color(0xFF1A2B37),
                          clipBehavior: Clip.antiAlias,
                          child: InkWell(
                            onTap: () => details(item.$2, item.$3),
                            child: Padding(
                              padding: const EdgeInsets.all(18),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Icon(item.$1, size: 28, color: primary),
                                  const SizedBox(height: 17),
                                  Text(item.$2, style: const TextStyle(
                                    fontSize: 18, fontWeight: FontWeight.bold)),
                                  const SizedBox(height: 8),
                                  Text(item.$3, maxLines: 3,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(
                                      color: Color(0xFFB5C9D4), height: 1.5)),
                                ],
                              ),
                            ),
                          ),
                        ), 90 * index);
                      },
                    );
                  }),
                  const SizedBox(height: 45),
                  const Center(child: Text('Diseñado con SKY Design Studio',
                    style: TextStyle(fontSize: 11, color: Color(0xFF8DA1AB)))),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
