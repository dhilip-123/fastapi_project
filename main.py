from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

app = FastAPI()

# MongoDB connection
client = AsyncIOMotorClient('mongodb://localhost:27017')
db = client.dhilip
collection = db.hotel

# Separate collection to manage auto-increment
counter_collection = db.counter

# Pydantic models for data validation
class HotelData(BaseModel):
    name: str
    email: EmailStr
    message: str

class UpdateHotelData(BaseModel):
    name: str = None
    email: EmailStr = None
    message: str = None

# Utility function to convert MongoDB document to a dictionary
def hotel_serializer(hotel) -> dict:
    return {
        "id": hotel["hotel_id"],
        "name": hotel["name"],
        "email": hotel["email"],
        "message": hotel["message"],
    }

# Function to generate the next auto-increment ID
async def get_next_hotel_id() -> str:
    counter = await counter_collection.find_one_and_update(
        {"_id": "hotel_id"}, 
        {"$inc": {"seq_value": 1}}, 
        upsert=True, 
        return_document=True
    )
    new_id = counter["seq_value"]
    return f"CID{new_id:04d}"

# POST API to submit data
@app.post("/submit", response_model=dict, status_code=status.HTTP_201_CREATED)
async def submit_data(hotel_data: HotelData):
    # Generate auto-incrementing ID
    hotel_id = await get_next_hotel_id()
    
    hotel_dict = hotel_data.dict()
    hotel_dict["hotel_id"] = hotel_id
    
    result = await collection.insert_one(hotel_dict)
    
    if result.inserted_id:
        new_hotel = await collection.find_one({"_id": result.inserted_id})
        return hotel_serializer(new_hotel)
    raise HTTPException(status_code=500, detail="Failed to add hotel data.")

# PUT API to update data by ID
@app.put("/update/{id}", response_model=dict)
async def update_data(id: str, hotel_data: UpdateHotelData):
    # Create the update query
    update_data = {k: v for k, v in hotel_data.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No data provided for update.")

    result = await collection.update_one({"hotel_id": id}, {"$set": update_data})

    if result.matched_count == 1:
        updated_hotel = await collection.find_one({"hotel_id": id})
        return hotel_serializer(updated_hotel)
    
    raise HTTPException(status_code=404, detail="Hotel data not found.")

# DELETE API to delete data by ID
@app.delete("/delete/{id}", response_model=dict)
async def delete_data(id: str):
    result = await collection.find_one({"hotel_id": id})
    
    if not result:
        raise HTTPException(status_code=404, detail="Hotel data not found.")
    
    delete_result = await collection.delete_one({"hotel_id": id})
    
    if delete_result.deleted_count == 1:
        return {"message": "Hotel data deleted successfully."}
    
    raise HTTPException(status_code=500, detail="Failed to delete hotel data.")
