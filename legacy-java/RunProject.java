import javax.swing.*;
import java.io.OutputStream;
import java.io.PrintStream;

public class RunProject {
    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> {
            JTextArea results = new JTextArea("Draw a digit (0–9) in one continuous stroke on the canvas.\nPress e in the canvas to exit.\n\nRecognized digits: ", 8, 48);
            results.setEditable(false);
            results.setLineWrap(true);
            JFrame output = new JFrame("Handwriting recognition — results");
            output.add(new JScrollPane(results));
            output.pack();
            output.setLocation(320, 80);
            output.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
            output.setVisible(true);
            PrintStream original = System.out;
            System.setOut(new PrintStream(new OutputStream() {
                public void write(int value) {
                    original.write(value);
                    SwingUtilities.invokeLater(() -> results.append(Character.toString((char) value)));
                }
            }, true));
            new Driver().start();
        });
    }
}
