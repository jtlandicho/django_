// Pin definitions for ultrasonic sensors
const int CAR_SENSORS[3][2] = {
  {2, 3},   // Car Slot 1 (TRIG_PIN, ECHO_PIN)
  {4, 5},   // Car Slot 2
  {6, 7}    // Car Slot 3
};

const int MOTORCYCLE_SENSORS[3][2] = {
  {8, 9},   // Motorcycle Slot 1
  {10, 11}, // Motorcycle Slot 2
  {12, 13}  // Motorcycle Slot 3
};

// Constants for vehicle detection
const float CAR_THRESHOLD = 100.0;        // Distance in cm for car detection
const float MOTORCYCLE_THRESHOLD = 50.0;  // Distance in cm for motorcycle detection
const int READINGS_COUNT = 3;             // Number of readings to average

void setup() {
  Serial.begin(9600);
  
  // Setup all sensor pins
  for(int i = 0; i < 3; i++) {
    pinMode(CAR_SENSORS[i][0], OUTPUT);      // TRIG pins as output
    pinMode(CAR_SENSORS[i][1], INPUT);       // ECHO pins as input
    pinMode(MOTORCYCLE_SENSORS[i][0], OUTPUT);
    pinMode(MOTORCYCLE_SENSORS[i][1], INPUT);
  }
  
  Serial.println("ParkSense Prototype - Sensor Readings");
  Serial.println("Format: [Slot Type] [Slot Number]: [Distance] cm - [Status]");
}

float getDistance(int trigPin, int echoPin) {
  float total = 0;
  
  // Take multiple readings and average them
  for(int i = 0; i < READINGS_COUNT; i++) {
    // Clear trigger pin
    digitalWrite(trigPin, LOW);
    delayMicroseconds(2);
    
    // Send 10μs pulse
    digitalWrite(trigPin, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigPin, LOW);
    
    // Read echo pin (returns pulse duration in microseconds)
    long duration = pulseIn(echoPin, HIGH);
    
    // Calculate distance in cm
    float distance = duration * 0.034 / 2;
    total += distance;
    
    delay(10);  // Short delay between readings
  }
  
  return total / READINGS_COUNT;
}

void checkSlots(const int sensors[][2], int numSlots, float threshold, const char* type) {
  for(int i = 0; i < numSlots; i++) {
    float distance = getDistance(sensors[i][0], sensors[i][1]);
    bool isOccupied = distance < threshold && distance > 0;
    
    Serial.print(type);
    Serial.print(" ");
    Serial.print(i + 1);
    Serial.print(": ");
    Serial.print(distance);
    Serial.print(" cm - ");
    Serial.println(isOccupied ? "Occupied" : "Available");
  }
}

void loop() {
  Serial.println("\n--- Current Readings ---");
  
  // Check car slots
  checkSlots(CAR_SENSORS, 3, CAR_THRESHOLD, "Car");
  
  // Check motorcycle slots
  checkSlots(MOTORCYCLE_SENSORS, 3, MOTORCYCLE_THRESHOLD, "Motorcycle");
  
  delay(1000);  // Update every second
}
