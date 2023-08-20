package main

import (
	"context"
	"fmt"
	"os"
	"strconv"
	"time"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
	"go.mongodb.org/mongo-driver/mongo/readpref"

	"github.com/gin-gonic/gin"
	"github.com/gin-contrib/cors"
	"net/http"
)

// Max Ads returned limit
const max_limit = 10000

// Timeout in Seconds
const timeout = 10

func min(a int64, b int64) int64 {
	if (a < b) {
		return a
	}
	return b
}

func connect_db() *mongo.Client {
	// Create a new client and connect to the server
	client, err := mongo.Connect(context.Background(), options.Client().ApplyURI(os.Getenv("DB_URL")))
	if err != nil {
		panic(err)
	}

	// Ping the primary
	if err := client.Ping(context.Background(), readpref.Primary()); err != nil {
		panic(err)
	}
	fmt.Println("Successfully connected and pinged the db.")

	return client
}

// Database and Collection
var client *mongo.Client = connect_db()
var db *mongo.Database = client.Database("facebook_ads_full")
var ads *mongo.Collection = db.Collection("ads")

// Get Total Ad count
// GET /total
func getTotalAds(c *gin.Context) {
	ctx, cancel := context.WithTimeout(context.Background(), timeout*time.Second)
	defer cancel()
	count, err := ads.EstimatedDocumentCount(ctx)
	if err != nil {
		c.String(http.StatusInternalServerError, "Failed to retrieve document count")
		return
	}
	c.String(http.StatusOK, strconv.FormatInt(count, 10))
}

// Single Ad Request
// GET /ad/id
func getAd(c *gin.Context) {
	ctx, cancel := context.WithTimeout(context.Background(), timeout*time.Second)
	defer cancel()
	id := c.Param("id")
	filter := bson.D{{"_id", id}}

	var result bson.M
	if err := ads.FindOne(ctx, filter).Decode(&result); err != nil {
		c.String(http.StatusNotFound, "Ad not found")
		return
	}
	c.JSON(http.StatusOK, result)
}

// Function to return Lists of Ads
func returnAdList(c *gin.Context, filter bson.D, sort bson.D) {
	ctx, cancel := context.WithTimeout(context.Background(), timeout*time.Second)
	defer cancel()

	param := c.DefaultQuery("offset", "0")
	offset, err := strconv.ParseInt(param, 10, 64)
	if err != nil {
		c.String(http.StatusBadRequest, "Invalid Offset")
		return
	}

	param2 := c.DefaultQuery("limit", "100")
	limit, err := strconv.ParseInt(param2, 10, 64)
	if err != nil {
		c.String(http.StatusBadRequest, "Invalid Limit")
		return
	}

	cursor, err := ads.Find(ctx, filter, options.Find().SetSort(sort).SetSkip(offset).SetLimit(min(limit, max_limit)))
	if err != nil {
		c.String(http.StatusInternalServerError, "Error finding ads")
		return
	}
	var result []bson.M
	if err = cursor.All(ctx, &result); err != nil {
		c.String(http.StatusInternalServerError, "Error unpacking ads")
		return
	}
	c.JSON(http.StatusOK, result)
}

// Ads by page
// GET /adbypage/page_id?offset=0
func getAdsByPage(c *gin.Context) {
	id := c.Param("id")
	filter := bson.D{{"page_id", id}}
	sort := bson.D{{"ad_creation_time", -1}}
	returnAdList(c, filter, sort)
}

// Search ads by page name
// GET /search/query?offset=0
func searchByPage(c *gin.Context) {
	search := c.Param("search")
	filter := bson.D{{"$text", bson.D{{"$search", search}}}}
	sort := bson.D{}
	returnAdList(c, filter, sort)
}

// Get lost ads
// GET /lostads?offset=0
func getLostAds(c *gin.Context) {
	filter := bson.D{{"lost", true}}
	sort := bson.D{{"ad_creation_time", -1}}
	returnAdList(c, filter, sort)
}

// Get active ads
// GET /actives
func getActives(c *gin.Context) {
	filter := bson.D{{"ad_delivery_start_time", bson.D{{"$exists", true}}}, {"ad_delivery_stop_time", nil}}
	sort := bson.D{{"ad_creation_time", -1}}
	returnAdList(c, filter, sort)
}

// Get latest ads
// GET /latest
func getLatest(c *gin.Context) {
	filter := bson.D{}
	sort := bson.D{{"$natural", -1}}
	returnAdList(c, filter, sort)
}

// Queue an Ad to preview rendering
// POST /render_preview/id
func queuePreview(c *gin.Context) {
	ctx, cancel := context.WithTimeout(context.Background(), timeout*time.Second)
	defer cancel()
	id := c.Param("id")
	filter := bson.D{{"_id", id}, {"rendered", bson.M{"$exists": false}}}
	update := bson.D{{"$set", bson.D{{"rendered", false}, {"rendering_started", 0}}}}

	result, err := ads.UpdateOne(ctx, filter, update)
	if err != nil {
		c.String(http.StatusInternalServerError, "Error updating the ad.")
		return
	}
	if result.MatchedCount == 0 {
		c.String(http.StatusNotFound, "Ad not found or already queued for rendering.")
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "Queued ad for rendering."})
}

func main() {
	defer func() {
		client.Disconnect(context.Background())
	}()

	router := gin.Default()
	router.Use(cors.Default())

	router.StaticFile("/", "frontend.html")
	router.GET("/total", getTotalAds)
	router.GET("/ad/:id", getAd)
	router.GET("/adsbypage/:id", getAdsByPage)
	router.GET("/search/:search", searchByPage)
	router.GET("/lostads", getLostAds)
	router.GET("/actives", getActives)
	router.GET("/latest", getLatest)
	router.POST("/render_preview/:id", queuePreview)
	router.POST("/addToken", addToken)

	router.Run()
}
