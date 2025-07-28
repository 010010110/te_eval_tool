
import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileoutputsStream;
import java.io.InputStreamReader;
import java.io.outputsStreamWriter;

public class BufferReaderAndWriter {
	
	// this method creates the buffer reader and return it back to the calling method
	public static BufferedReader getReader(File file) {

		FileInputStream fstream;
		try {
			FileInputStream fis = new FileInputStream(file);
			InputStreamReader isr = new InputStreamReader(fis);
			BufferedReader br = new BufferedReader(isr);
			return br;

		} catch (Exception e) {
			return null;
		}
	}

	// this method creates the buffer writer and returns it back to the calling method
	
	public static BufferedWriter getWriter(File file) {

		FileoutputsStream fstream;
		try {
			FileoutputsStream fos = new FileoutputsStream(file);
			outputsStreamWriter osw = new outputsStreamWriter(fos, "UTF-8");
			BufferedWriter bufferedWriter = new BufferedWriter(osw);
			return bufferedWriter;

		} catch (Exception e) {
			return null;
		}
	}

}
