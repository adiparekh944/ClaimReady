/**
 * Hardcoded room data for ClaimReady frontend
 * Provides predefined data for specific room images, bypassing backend ML pipeline
 */

export interface HardcodedItem {
  code: string;
  imageAttachment: string;
  bbox: [number, number, number, number];
  name: string;
  category: string;
  price_usd: number;
  description: string;
}

export interface HardcodedResponse {
  items: HardcodedItem[];
  objects: number[][];
  images: Record<string, string>;
  hardcoded: boolean;
  room: string;
}

// Hardcoded room data
const hardcodedRooms: Record<string, HardcodedItem[]> = {
  "sv-dorm.jpg": [
    { code: "0", imageAttachment: "crop0", bbox: [100, 150, 300, 400], name: "Assorted EA", category: "Textiles", price_usd: 60, description: "A collection of assorted items" },
    { code: "1", imageAttachment: "crop1", bbox: [350, 200, 500, 350], name: "Black Back", category: "Luggage", price_usd: 100, description: "A black backpack" },
    { code: "2", imageAttachment: "crop2", bbox: [600, 100, 750, 250], name: "Black Harc", category: "Furniture", price_usd: 70, description: "A black hard case" },
    { code: "3", imageAttachment: "scene", bbox: [50, 50, 200, 300], name: "Black Offic", category: "Office Sup", price_usd: 25, description: "A black office item" },
    { code: "4", imageAttachment: "crop3", bbox: [100, 450, 300, 600], name: "Clear Plas", category: "Storage", price_usd: 15, description: "A clear plastic container" },
    { code: "5", imageAttachment: "scene", bbox: [400, 100, 600, 200], name: "Dark Plast", category: "Storage", price_usd: 200, description: "A dark plastic item" },
    { code: "6", imageAttachment: "crop4", bbox: [200, 300, 400, 500], name: "Desktop C", category: "Electronic", price_usd: 30, description: "A desktop computer" },
    { code: "7", imageAttachment: "scene", bbox: [500, 400, 700, 600], name: "Ergonomic", category: "Office Sup", price_usd: 20, description: "An ergonomic office chair" },
    { code: "8", imageAttachment: "crop5", bbox: [150, 200, 350, 400], name: "Ganesha F", category: "Home Dec", price_usd: 5, description: "A Ganesha figurine" },
    { code: "9", imageAttachment: "scene", bbox: [300, 150, 500, 300], name: "Green Coll", category: "Apparel", price_usd: 10, description: "A green collar" },
    { code: "10", imageAttachment: "crop6", bbox: [100, 100, 300, 200], name: "Grey Desk", category: "Furniture", price_usd: 2, description: "A grey desk" },
    { code: "11", imageAttachment: "scene", bbox: [400, 300, 600, 500], name: "Lip Balm S", category: "Personal C", price_usd: 180, description: "A lip balm set" },
    { code: "12", imageAttachment: "crop7", bbox: [200, 400, 400, 600], name: "Plaid Flanr", category: "Textiles", price_usd: 50, description: "A plaid flannel item" },
    { code: "13", imageAttachment: "scene", bbox: [100, 500, 300, 700], name: "Purell Han", category: "Personal C", price_usd: 300, description: "A Purell hand sanitizer" },
    { code: "14", imageAttachment: "crop8", bbox: [500, 200, 700, 400], name: "Red Toy C", category: "Toys", price_usd: 40, description: "A red toy car" },
    { code: "15", imageAttachment: "scene", bbox: [300, 600, 500, 800], name: "Round Wo", category: "Furniture", price_usd: 250, description: "A round wooden item" },
    { code: "16", imageAttachment: "crop9", bbox: [150, 300, 350, 500], name: "Small Note", category: "Books", price_usd: 80, description: "A small notebook" },
    { code: "17", imageAttachment: "scene", bbox: [400, 700, 600, 900], name: "Sonos Wire", category: "Electronic", price_usd: 150, description: "A Sonos wireless speaker" },
    { code: "18", imageAttachment: "crop10", bbox: [200, 100, 400, 300], name: "Stack of Bo", category: "Books", price_usd: 20, description: "A stack of books" },
    { code: "19", imageAttachment: "scene", bbox: [500, 500, 700, 700], name: "Stack of D", category: "Storage", price_usd: 15, description: "A stack of documents" },
    { code: "20", imageAttachment: "crop11", bbox: [100, 200, 300, 400], name: "Textured A", category: "Home Dec", price_usd: 10, description: "A textured art piece" },
    { code: "21", imageAttachment: "scene", bbox: [300, 400, 500, 600], name: "Twin XL Ma", category: "Textiles", price_usd: 2, description: "A Twin XL mattress" },
    { code: "22", imageAttachment: "crop12", bbox: [400, 200, 600, 400], name: "USB Cable", category: "Electronic", price_usd: 180, description: "A USB cable" },
    { code: "23", imageAttachment: "scene", bbox: [200, 700, 400, 900], name: "Vertical De", category: "Furniture", price_usd: 50, description: "A vertical desk" },
    { code: "24", imageAttachment: "crop13", bbox: [500, 100, 700, 300], name: "Wall Moun", category: "Home Dec", price_usd: 300, description: "A wall mounted item" },
    { code: "25", imageAttachment: "scene", bbox: [100, 800, 300, 1000], name: "White Bed", category: "Furniture", price_usd: 40, description: "A white bed frame" },
    { code: "26", imageAttachment: "crop14", bbox: [300, 200, 500, 400], name: "White Esse", category: "Home Dec", price_usd: 250, description: "A white essential item" },
    { code: "27", imageAttachment: "scene", bbox: [400, 400, 600, 600], name: "White Mult", category: "Electronic", price_usd: 80, description: "A white multi-purpose device" },
    { code: "28", imageAttachment: "crop15", bbox: [200, 500, 400, 700], name: "Window wi", category: "Architectu", price_usd: 150, description: "A window with frame" },
    { code: "29", imageAttachment: "scene", bbox: [500, 300, 700, 500], name: "Wireless C", category: "Electronic", price_usd: 20, description: "A wireless charger" },
    { code: "30", imageAttachment: "crop16", bbox: [100, 300, 300, 500], name: "Wisconsin A", category: "Home Dec", price_usd: 15, description: "A Wisconsin art piece" },
    { code: "31", imageAttachment: "scene", bbox: [300, 600, 500, 800], name: "Wooden B", category: "Furniture", price_usd: 10, description: "A wooden bench" },
    { code: "32", imageAttachment: "crop17", bbox: [400, 100, 600, 300], name: "Wooden D", category: "Furniture", price_usd: 2, description: "A wooden desk" },
    { code: "33", imageAttachment: "scene", bbox: [500, 400, 700, 600], name: "Wooden St", category: "Furniture", price_usd: 15, description: "A wooden stool" }
  ],
  
  "room3.jpg": [
    { code: "0", imageAttachment: "crop0", bbox: [100, 150, 300, 400], name: "Bar Stool", category: "Furniture", price_usd: 70, description: "A wooden bar stool" },
    { code: "1", imageAttachment: "crop1", bbox: [350, 200, 500, 350], name: "Flat Screei", category: "Electronic", price_usd: 350, description: "A small black flat screen TV" },
    { code: "2", imageAttachment: "crop2", bbox: [600, 100, 750, 250], name: "Green Sofa", category: "Furniture", price_usd: 800, description: "A white three-seater sofa" },
    { code: "3", imageAttachment: "scene", bbox: [50, 50, 200, 300], name: "Magazines", category: "Media", price_usd: 10, description: "A colorful magazine collection" },
    { code: "4", imageAttachment: "crop3", bbox: [100, 450, 300, 600], name: "Dining Table", category: "Furniture", price_usd: 250, description: "A black flat dining table" },
    { code: "5", imageAttachment: "scene", bbox: [400, 100, 600, 200], name: "Framed Fo", category: "Decor", price_usd: 40, description: "A framed photo" },
    { code: "6", imageAttachment: "crop4", bbox: [200, 300, 400, 500], name: "Another el", category: "Decor", price_usd: 40, description: "Another element" },
    { code: "7", imageAttachment: "scene", bbox: [500, 400, 700, 600], name: "Soft gray", category: "Textiles", price_usd: 40, description: "A soft gray throw pillow" },
    { code: "8", imageAttachment: "crop5", bbox: [150, 200, 350, 400], name: "Modern", category: "Furniture", price_usd: 200, description: "A modern furniture piece" },
    { code: "9", imageAttachment: "scene", bbox: [300, 150, 500, 300], name: "Light-colo", category: "Textiles", price_usd: 100, description: "A light-colored textile" },
    { code: "10", imageAttachment: "crop6", bbox: [100, 100, 300, 200], name: "Large dark", category: "Furniture", price_usd: 300, description: "A large dark furniture piece" },
    { code: "11", imageAttachment: "scene", bbox: [400, 300, 600, 500], name: "Orange", category: "Decor", price_usd: 15, description: "An orange decorative item" },
    { code: "12", imageAttachment: "crop7", bbox: [200, 400, 400, 600], name: "Colorful p", category: "Decor", price_usd: 25, description: "A colorful patterned item" },
    { code: "13", imageAttachment: "scene", bbox: [100, 500, 300, 700], name: "Decorative", category: "Decor", price_usd: 40, description: "A decorative element" },
    { code: "14", imageAttachment: "crop8", bbox: [500, 200, 700, 400], name: "Electro", category: "Electronic", price_usd: 50, description: "A small electronic device" },
    { code: "15", imageAttachment: "scene", bbox: [300, 600, 500, 800], name: "Small bla", category: "Electronic", price_usd: 40, description: "A small black electronic device" },
    { code: "16", imageAttachment: "crop9", bbox: [150, 300, 350, 500], name: "Small bla", category: "Electronic", price_usd: 50, description: "Another small black device" },
    { code: "17", imageAttachment: "scene", bbox: [400, 700, 600, 900], name: "Small rou", category: "Decor", price_usd: 15, description: "A small round decorative item" },
    { code: "18", imageAttachment: "crop10", bbox: [200, 100, 400, 300], name: "Stack of Bo", category: "Media", price_usd: 25, description: "A stack of books" },
    { code: "19", imageAttachment: "scene", bbox: [500, 500, 700, 700], name: "Wall-mour", category: "Decor", price_usd: 30, description: "A wall-mounted shelf" },
    { code: "20", imageAttachment: "crop11", bbox: [100, 200, 300, 400], name: "White ce", category: "Decor", price_usd: 35, description: "A white ceramic vase" },
    { code: "21", imageAttachment: "scene", bbox: [300, 400, 500, 600], name: "Natural v", category: "Decor", price_usd: 20, description: "A natural wood element" },
    { code: "22", imageAttachment: "crop12", bbox: [400, 200, 600, 400], name: "Standard t", category: "Textiles", price_usd: 150, description: "A standard textile item" },
    { code: "23", imageAttachment: "scene", bbox: [200, 700, 400, 900], name: "Rustic wo", category: "Furniture", price_usd: 200, description: "A rustic wooden piece" },
    { code: "24", imageAttachment: "crop13", bbox: [500, 100, 700, 300], name: "Rustic wo", category: "Furniture", price_usd: 150, description: "Another rustic wooden item" },
    { code: "25", imageAttachment: "scene", bbox: [100, 800, 300, 1000], name: "Bright ye", category: "Decor", price_usd: 25, description: "A bright yellow decorative item" }
  ],
  
  "arnav-hotel.jpeg": [
    { code: "0", imageAttachment: "crop0", bbox: [100, 150, 300, 400], name: "Accent Dir", category: "Furniture", price_usd: 120, description: "A modern accent chair" },
    { code: "1", imageAttachment: "crop1", bbox: [350, 200, 500, 350], name: "Bed Frame", category: "Furniture", price_usd: 800, description: "A modern upholstered bed frame" },
    { code: "2", imageAttachment: "crop2", bbox: [600, 100, 750, 250], name: "Bedroom E", category: "Furniture", price_usd: 180, description: "A bedroom essential item" },
    { code: "3", imageAttachment: "scene", bbox: [50, 50, 200, 300], name: "Built-in Ca", category: "Furniture", price_usd: 700, description: "Part of a built-in cabinet system" },
    { code: "4", imageAttachment: "crop3", bbox: [100, 450, 300, 600], name: "Full Built-in", category: "Furniture", price_usd: 1500, description: "A comprehensive built-in storage system" },
    { code: "5", imageAttachment: "scene", bbox: [400, 100, 600, 200], name: "Lounge Arr", category: "Furniture", price_usd: 1500, description: "A black leather lounge chair" },
    { code: "6", imageAttachment: "crop4", bbox: [200, 300, 400, 500], name: "Mattress", category: "Textiles", price_usd: 1200, description: "A white mattress" },
    { code: "7", imageAttachment: "scene", bbox: [500, 400, 700, 600], name: "Round Din", category: "Furniture", price_usd: 250, description: "A small round dining table" },
    { code: "8", imageAttachment: "crop5", bbox: [150, 200, 350, 400], name: "Slatted Wo", category: "Furniture", price_usd: 400, description: "An integrated slatted wood headboard" },
    { code: "9", imageAttachment: "scene", bbox: [300, 150, 500, 300], name: "Small Rour", category: "Furniture", price_usd: 80, description: "A small dark furniture piece" },
    { code: "10", imageAttachment: "crop6", bbox: [100, 100, 300, 200], name: "Area Rug", category: "Textiles", price_usd: 300, description: "A neutral-toned area rug" },
    { code: "11", imageAttachment: "scene", bbox: [400, 300, 600, 500], name: "Window Ci", category: "Textiles", price_usd: 150, description: "Full-length window curtains" },
    { code: "12", imageAttachment: "crop7", bbox: [200, 400, 400, 600], name: "Coffee Cup", category: "Tableware", price_usd: 15, description: "A white ceramic coffee cup" },
    { code: "13", imageAttachment: "scene", bbox: [100, 500, 300, 700], name: "Decorative", category: "Decoration", price_usd: 40, description: "A small decorative item" },
    { code: "14", imageAttachment: "crop8", bbox: [500, 200, 700, 400], name: "Decorative", category: "Decoration", price_usd: 40, description: "Another small decorative item" },
    { code: "15", imageAttachment: "scene", bbox: [300, 600, 500, 800], name: "Framed W", category: "Decoration", price_usd: 80, description: "A square framed wall art" },
    { code: "16", imageAttachment: "crop9", bbox: [150, 300, 350, 500], name: "Framed W", category: "Decoration", price_usd: 100, description: "A rectangular framed wall art" },
    { code: "17", imageAttachment: "scene", bbox: [400, 700, 600, 900], name: "Duvet/Cor", category: "Bedding", price_usd: 250, description: "A white duvet cover" },
    { code: "18", imageAttachment: "crop10", bbox: [200, 100, 400, 300], name: "Pillow Set", category: "Bedding", price_usd: 150, description: "Two white pillows" },
    { code: "19", imageAttachment: "scene", bbox: [500, 500, 700, 700], name: "Pillow Set", category: "Bedding", price_usd: 150, description: "Another set of white pillows" },
    { code: "20", imageAttachment: "crop11", bbox: [100, 200, 300, 400], name: "Modern Flo", category: "Lighting", price_usd: 180, description: "A tall floor lamp" },
    { code: "21", imageAttachment: "scene", bbox: [300, 400, 500, 600], name: "Pair of Sho", category: "Apparel", price_usd: 100, description: "A dark-colored pair of shoes" },
    { code: "22", imageAttachment: "crop12", bbox: [400, 200, 600, 400], name: "Wall-Mour", category: "Electronic", price_usd: 600, description: "A flat-screen wall-mounted TV" },
    { code: "23", imageAttachment: "scene", bbox: [200, 700, 400, 900], name: "Window", category: "Architectu", price_usd: 500, description: "A window with visible frame" }
  ]
};

/**
 * Check if a filename corresponds to a hardcoded room
 */
export function isHardcodedRoom(filename: string): boolean {
  return filename.toLowerCase() in hardcodedRooms;
}

/**
 * Get hardcoded response for a room image
 */
export function getHardcodedResponse(filename: string): HardcodedResponse | null {
  const roomData = hardcodedRooms[filename.toLowerCase()];
  
  if (!roomData) {
    return null;
  }
  
  // Create mock objects data (bounding boxes for visualization)
  const objects = roomData.map(item => [
    item.bbox[0], item.bbox[1], item.bbox[2], item.bbox[3], 1.0 // confidence = 1.0 for hardcoded items
  ]);
  
  // Create mock images data (empty for now, could add placeholder images)
  const images: Record<string, string> = {};
  
  return {
    items: roomData,
    objects,
    images,
    hardcoded: true,
    room: filename
  };
}

/**
 * Get list of available hardcoded rooms
 */
export function getAvailableHardcodedRooms(): string[] {
  return Object.keys(hardcodedRooms);
}

/**
 * Calculate total value for hardcoded items
 */
export function calculateHardcodedTotalValue(items: HardcodedItem[]): number {
  return items.reduce((total, item) => total + item.price_usd, 0);
}
