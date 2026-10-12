import java.awt.event.*;

/**
 * This is the driver for the unistroke handwriting recognition algorithm. The
 * driver sets up a drawing surface and collects points as the user moves draws
 * a stroke on the surface. The driver uses an instance of a Recognizer class to
 * store the user's input, process it, and to compare it to inputs in a base
 * set. The best match is then returned and printed.
 * 
 * Instructions: Run the function named "start" from BlueJ Draw a unistroke
 * representing one of the digits 0 through 9 on the canvas The recognized
 * character will be printed in an output window Continue drawing strokes until
 * you are done Press "e" to exit the program -- exiting in other ways
 * 
 * @author Dave Berque
 * @version August, 2004
 * 
 * Slightly modified by David E. Maharry 10/27/2004
 * 
 */
public class Driver implements KeyListener, MouseListener, MouseMotionListener {
    private static final int STROKESIZE = 150;
    private Circle[] myCircle; // Used to trace out the user's stroke
    private Canvas myCanvas; // The drawing surface
    public Recognizer myRecognizer; // Performs the unistroke recognition

    private int currentCircle;

    /**
     * Constructor for objects of class driver
     */
    public Driver()
    {
        myCanvas = new Canvas();
        myCircle = new Circle[STROKESIZE];
        for (int i = 0; i < myCircle.length; i++) {
            myCircle[i] = new Circle(myCanvas);
        }
        myRecognizer = new Recognizer();
    }

    // Run the following function from the BlueJay environment to start things
    // off
    public void start()
    {
        myCanvas.setListener(this);
        myCanvas.setVisible(true);
        currentCircle = 0;
    }

    // Run this from the BlueJay menu to see the last stroke replayed. This
    // will test the preprocessing for debugging. This function is not used
    // except for debugging
    public void playBack()
    {
        for (int i = 0; i < myRecognizer.numUserPoints(); i++) {
            myCircle[i].moveTo(myRecognizer.getUserPointX(i), myRecognizer
                    .getUserPointY(i));
            myCircle[i].makeVisible();
        }
    }

    // Keyboard listeners
    public void keyPressed(KeyEvent ke)
    {
        if (ke.getKeyChar() == 'e')
            System.exit(0);
    }

    // Mouse listeners and mouse motion listeners

    // When the mouse button is pressed (or pen-tip is depressed) prepare to
    // collect points for the new stroke and collect the starting point adding
    // it to the recognizer class.
    public void mousePressed(MouseEvent event)
    {
        myCanvas.eraseAll();
        currentCircle = 0; // starts a new stroke
        myCircle[currentCircle].moveTo(event.getPoint().x, event.getPoint().y);
        myCircle[currentCircle].makeVisible();
        myRecognizer.resetUserStroke();
        myRecognizer.addUserPoint(event.getPoint());
    }

    // As the mouse moves, add points to the recognizer class. The recognizer
    // class
    // will ignore any points which exceed the maximum number of points it can
    // store in a
    // single stroke.
    public void mouseDragged(MouseEvent event)
    {

        currentCircle = currentCircle + 1;
        if (currentCircle == STROKESIZE) {
            currentCircle = STROKESIZE - 1;
        }
        myCircle[currentCircle].moveTo(event.getPoint().x, event.getPoint().y);
        myCircle[currentCircle].makeVisible();
        myRecognizer.addUserPoint(event.getPoint());
    }

    // When the mouse is released process the user's stroke by translating,
    // scaling,
    // and point normalizing it. Then find the best match from the base set and
    // print
    // the result.
    public void mouseReleased(MouseEvent event)
    {
        // Make the circle that traces out the user's stroke invisible
        // myCircle[0].makeInvisible();
        findMatch();
    }

    // Unused mouse listeners, mouse motion listeners, and keyboard listeners
    // empty definitions are required
    public void mouseClicked(MouseEvent event)
    {
    }

    public void mouseEntered(MouseEvent event)
    {
    }

    public void mouseExited(MouseEvent event)
    {
    }

    public void mouseMoved(MouseEvent event)
    {
    }

    public void keyTyped(KeyEvent ke)
    {
    }

    public void keyReleased(KeyEvent ke)
    {
    }

    /**
     * findMatch - compares the user's image with the reference images and
     * prints the best match
     */
    public void findMatch()
    {
        // Find and print the best match
        System.out.print(myRecognizer.findMatch() + " ");
    }
}
