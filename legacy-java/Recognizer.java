import java.awt.Point;
import java.io.*;

/**
 * This class performs unistroke handwriting recognition using an algorithm
 * known as "elastic matching."
 * 
 * @author Dave Berque
 * @version August, 2004 Slightly modified by David E. Maharry and Carl Singer
 *          10/27/2004
 * 
 */

public class Recognizer {
    public static final int STROKESIZE = 150; // Max number of points in each
                                                // stroke
    private static final int NUMSTROKES = 10; // Number of strokes in the base
                                                // set (0 through 9)
    private Point[] userStroke; // holds points that comprise the user's stroke
    private int nextFree; // next free cell of the userStroke array

    private Point[][] baseSet; // holds points for each stroke (0-9) in the
                                // base set.

    // baseset is an array of arrays, a 2-D array.

    /**
     * Constructor for the recognizer class. Sets up the arrays and loads the
     * base set from an existing data file which is assumed to have the right
     * number of points in it. The file is organized so that there are 150
     * points for stroke 0 followed by 150 points for stroke 1, ... 150 poinpts
     * for stroke 9. Each stroke is organized as an alternating series of x, y
     * pairs. For example, stroke 0 consists of 300 lines with the first line
     * being x0 for stroke 0, the next line being y0 for stroke 0, the next line
     * being x1 for stroke 0 and so on.
     */
    public Recognizer()
    {
        int row, col, stroke, pointNum, x, y;
        String inputLine;

        userStroke = new Point[STROKESIZE];
        baseSet = new Point[NUMSTROKES][STROKESIZE];

        try {
            FileReader myReader = new FileReader("strokedata.txt");
            BufferedReader myBufferedReader = new BufferedReader(myReader);
            for (stroke = 0; stroke < NUMSTROKES; stroke++)
                for (pointNum = 0; pointNum < STROKESIZE; pointNum++) {
                    inputLine = myBufferedReader.readLine();
                    x = Integer.parseInt(inputLine);
                    inputLine = myBufferedReader.readLine();
                    y = Integer.parseInt(inputLine);
                    baseSet[stroke][pointNum] = new Point(x, y);
                }
            myBufferedReader.close();
            myReader.close();
        }
        catch (IOException e) {
            System.out.println("Error writing to file.\n");
        }
    }

    public void translate()
    {
        int x = findMinX(); //find the minimum x value in the userStroke
        int y = findMinY(); //find the minimum y value in the userStroke
        //For each point in the userStroke, subtract the minimum x and y values from its coordinates.
        for(int i = 0; i<nextFree;i++)
        {
            userStroke[i].x = userStroke[i].x-x; 
            userStroke[i].y = userStroke[i].y-y;
        }
    }
    /**
     * translate - Translates the points in the userStroke array by sliding them
     * as far to the upper-left as possible. It does this by finding the minX
     * value and the minY value. Then each point (x, y) is replaced with the
     * point (x-minX, y-minY). Note: you can use the translate method of the
     * Point class
     */

    public void scale()
    {
        //find the scaling factor by comparing the maximum x and y values in the userStroke
        //scale each point's x and y coordinates by a factor that will make the maximum x or y value equal to 250.
        double scaleFactor;
        if(findMaxX() > findMaxY())
            scaleFactor = 250.0/(double) findMaxX();
        else
            scaleFactor = 250.0/(double) findMaxY();
        //// this loop scales each point in the userStroke array by multiplying its x and y values by the scaling factor.
            for(int i = 0; i<nextFree; i++)
        {
            userStroke[i].x = (int) (userStroke[i].x*scaleFactor);
            userStroke[i].y = (int) (userStroke[i].y*scaleFactor);            
        }
    }
    /**
     * scale - Scales the points in the user array by stretching the user's
     * stroke to fill the canvas as nearly as possible while maintaining the
     * aspect ratio of the stroke.
     */
    /**
     * insertOnePoint - inserts a new point between the two points that are the
     * farthest apart in the userStroke array. There must be at least two points
     * in the array
     */
    private void insertOnePoint()
    {
        // This method inserts a new point into the userStroke array by 
        //finding the maximum distance between the first point in the 
        //array and all other points in the array and then inserting a 
        //new point at the midpoint between this maximum distance.
        int maxPosition = 0, newX, newY, distance;
        // compute distance between point 0 and point 1
        int maxDistance = (int) userStroke[0].distance(userStroke[1]);
        for(int i = 1; i<nextFree-1; i++)
        {
            distance = (int) userStroke[0].distance(userStroke[i+1]);
            if(distance>maxDistance)
            {
                maxDistance = distance;
                maxPosition = i;
            }
        }
        // slide that are to the right of cell maxPosition right by one
        for (int i = nextFree; i > maxPosition + 1; i--)
            userStroke[i] = userStroke[i - 1];

        // Insert the average
        newX = (int) (userStroke[maxPosition].getX() + userStroke[maxPosition + 2]
                .getX()) / 2;
        newY = (int) (userStroke[maxPosition].getY() + userStroke[maxPosition + 2]
                .getY()) / 2;
        userStroke[maxPosition + 1] = new Point(newX, newY);

        nextFree++;
    }

    /**
     * normalizeNumPoints - Adds points to the userStroke by inserting points
     * repeatedly until there are STROKESIZE points in the stroke
     */
    public void normalizeNumPoints()
    {
        while (nextFree < STROKESIZE) {
            insertOnePoint();
        }
    }

    public double computeScore(int digitToCompare)
    {
        //this method computes the score between the userStroke array 
        //and a digit in the baseSet array by summing up the distances 
        //between each point in the two arrays.
        double score = 0;
        for (int i = 0; i<nextFree; i++)
        {
            score = score + userStroke[i].distance(baseSet[digitToCompare][i]);
        }
        return score;
    }    
    /**
     * computeScore Computes and returns a "score" that is a measure of how
     * closely the normalized userStroke array matches a given pattern array in
     * the baseset array. The score is the sum of the distances between
     * corresponding points in the userStroke array and the pattern array.
     * 
     * @param digitToCompare
     *            The index of the pattern in the baseset with which to compute
     *            the score
     */

    /**
     * findMatch - Finds and returns the index (an int) of the base set pattern
     * which most closely matches the user stroke.
     */
    public int findMatch()
    {
        //get the index (an integer) of the base set pattern most closely matching the user stroke.
        translate();
        scale();
        normalizeNumPoints();
        double min = computeScore(0);
        int match = 0;
        for (int i = 1; i<=9; i++)
        {
            if (min>computeScore(i))
            {
                min = computeScore(i);
                match = i;
            }
        }
        return match;
    }

    /**
     * findMinX - returns the smallest x value in the userStroke array of points
     */
    public int findMinX() //find the minimum x value in the userStroke
    {
        int minX = userStroke[0].x;
        for(int i = 1; i < nextFree; i++)
        {
            if(userStroke[i].x<minX)
                minX = userStroke[i].x;
        }
        return minX;
    }

    /**
     * findMinY - returns the smallest y value in the userStroke array of points
     */
    public int findMinY() //find the minimum y value in the userStroke
    {
        int minY = userStroke[0].y;
        for(int i = 1; i < nextFree; i++)
        {
            if(userStroke[i].y<minY)
                minY = userStroke[i].y;
        }
        return minY;
    }
 
    /**
     * findMaxX - returns the largest x value in the userStroke array of points
     */
    public int findMaxX() //find the maximum x value in the userStroke
    {
        int maxX = userStroke[0].x;
        for(int i = 1; i < nextFree; i++)
        {
            if(userStroke[i].x>maxX)
                maxX = userStroke[i].x;
        }
        return maxX;
    }

    /**
     * findMaxY - returns the largest y value in the userStroke array of points
     */
    public int findMaxY() //find the maximum y value in the userStroke
    {
        int maxY = userStroke[0].y;
        for(int i = 1; i < nextFree; i++)
        {
            if(userStroke[i].y>maxY)
                maxY = userStroke[i].y;
        }
        return maxY;
    }
    
    public void resetUserStroke()
    {
        nextFree = 0;
    }

    // Returns the number of points currently in the user stroke array.
    public int numUserPoints()
    {
        return nextFree;
    }

    // This returns the x portion of the i'th point in the user array
    public int getUserPointX(int i)
    {
        if ((i >= 0) && (i < nextFree))
            return ((int) userStroke[i].getX());
        else {
            System.out.println("Invalid value of i in getUserPoint");
            return (0);
        }
    }

    // This returns the y portion of the i'th point in the user array
    public int getUserPointY(int i)
    {
        if ((i >= 0) && (i < nextFree))
            return ((int) userStroke[i].getY());
        else {
            System.out.println("Invalid value of i in getUserPoint");
            return (0);
        }
    }

    public void addUserPoint(Point newPoint)
    {
        if (nextFree < STROKESIZE) {
            userStroke[nextFree] = newPoint;
            nextFree++;
        }
    }
}
