// The Java side of tools/sonar-local.py: runs the checks of SonarSource's open Python analyzer (sonar-python-plugin)
// over a list of files and prints what they find. Started by sonar-local.py in Java's source-file mode:
//
//     java -cp <plugin jar>:<plugin api jar>:<slf4j jar> tools/SonarLocal.java <plugin jar> <rule keys> <file list>
//
// <rule keys> holds one active rule key per line (S1192, …). <file list> holds one file per line, "main<TAB>path" or
// "test<TAB>path"; a check whose scope is MAIN skips a test file, as SonarQube Cloud does.
// Output, tab-separated: "RULES <loaded>", "MISSING <key>" for an active key the plugin has no check for,
// "ISSUE <path> <line> <key> <message>" and "PARSE <path> <line> <message>".

import java.io.File;
import java.lang.reflect.Modifier;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import java.util.jar.JarEntry;
import java.util.jar.JarFile;
import org.sonar.check.Rule;
import org.sonar.plugins.python.api.PythonCheck;
import org.sonar.plugins.python.api.PythonSubscriptionCheck;
import org.sonar.plugins.python.api.PythonVisitorContext;
import org.sonar.python.SubscriptionVisitor;
import org.sonar.python.TestPythonVisitorRunner;

public class SonarLocal {
  private static final String CHECKS = "org/sonar/python/checks/";

  public static void main(String[] args) throws Exception {
    Set<String> active = new HashSet<>(Files.readAllLines(Path.of(args[1])));
    active.removeIf(String::isBlank);
    List<PythonCheck> checks = loadChecks(args[0], active);
    System.out.println("RULES\t" + checks.size());
    Set<String> missing = new TreeSet<>(active);
    for (PythonCheck check : checks) {
      missing.remove(key(check));
    }
    for (String key : missing) {
      System.out.println("MISSING\t" + key);
    }
    for (String line : Files.readAllLines(Path.of(args[2]))) {
      String[] parts = line.split("\t", 2);
      if (parts.length == 2) {
        analyze(checks, new File(parts[1]), "test".equals(parts[0]));
      }
    }
  }

  // Every check class of the plugin with an active rule key; TestPythonVisitorRunner.scanFile would run none.
  private static List<PythonCheck> loadChecks(String pluginJar, Set<String> active) throws Exception {
    List<PythonCheck> checks = new ArrayList<>();
    try (JarFile jar = new JarFile(pluginJar)) {
      for (Enumeration<JarEntry> entries = jar.entries(); entries.hasMoreElements();) {
        String name = entries.nextElement().getName();
        if (name.startsWith(CHECKS) && name.endsWith(".class") && !name.contains("$")) {
          Class<?> type = Class.forName(name.substring(0, name.length() - 6).replace('/', '.'));
          Rule rule = type.getAnnotation(Rule.class);
          if (rule != null && active.contains(rule.key()) && PythonCheck.class.isAssignableFrom(type)
              && !Modifier.isAbstract(type.getModifiers())) {
            checks.add((PythonCheck) type.getDeclaredConstructor().newInstance());
          }
        }
      }
    }
    return checks;
  }

  private static String key(PythonCheck check) {
    return check.getClass().getAnnotation(Rule.class).key();
  }

  private static void analyze(List<PythonCheck> checks, File file, boolean test) {
    PythonVisitorContext context = TestPythonVisitorRunner.createContext(file);
    if (context.parsingException() != null) {
      System.out.println("PARSE\t" + file + "\t" + context.parsingException().getLine() + "\t"
          + context.parsingException().getMessage().replace('\n', ' '));
      return;
    }
    List<PythonSubscriptionCheck> subscriptions = new ArrayList<>();
    for (PythonCheck check : checks) {
      if (test && check.scope() == PythonCheck.CheckScope.MAIN) {
        continue;
      }
      if (check instanceof PythonSubscriptionCheck subscription) {
        subscriptions.add(subscription);
      } else {
        check.scanFile(context);
      }
    }
    SubscriptionVisitor.analyze(subscriptions, context);
    for (PythonCheck.PreciseIssue issue : context.getIssues()) {
      Integer line = issue.primaryLocation().startLine();
      String message = issue.primaryLocation().message();
      System.out.println("ISSUE\t" + file + "\t" + line + "\t" + key(issue.check()) + "\t"
          + (message == null ? "" : message.replace('\n', ' ')));
    }
  }
}
