package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
	"go.mongodb.org/mongo-driver/mongo/readpref"

	"net/http"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
)

// Max Ads returned limit
const max_limit = 10000

// Max offset
const max_offset = 100000

// Timeout in Seconds
const timeout = 30

func min(a int64, b int64) int64 {
	if a < b {
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
var tokens *mongo.Collection = db.Collection("tokens")
var render_queue *mongo.Collection = db.Collection("render_queue")

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
	filter := bson.M{"_id": id}

	var result bson.M
	if err := ads.FindOne(ctx, filter).Decode(&result); err != nil {
		c.String(http.StatusNotFound, "Ad not found")
		return
	}
	c.JSON(http.StatusOK, result)
}

// Function to return Lists of Ads
func returnAdList(c *gin.Context, filter interface{}, sort interface{}) {
	ctx, cancel := context.WithTimeout(context.Background(), timeout*time.Second)
	defer cancel()

	offset_param := c.DefaultQuery("offset", "0")
	offset, err := strconv.ParseInt(offset_param, 10, 64)
	if err != nil {
		c.String(http.StatusBadRequest, "Invalid Offset")
		return
	}

	if offset > max_offset {
		c.String(http.StatusBadRequest, "Offset too high, this endpoint is not meant for bulk requests.")
		return
	}

	limit_param := c.DefaultQuery("limit", "100")
	limit, err := strconv.ParseInt(limit_param, 10, 64)
	if err != nil {
		c.String(http.StatusBadRequest, "Invalid Limit")
		return
	}

	fields_param := c.DefaultQuery("fields", "")
	projection := bson.M{}
	if fields_param != "" {
		projection = bson.M{}
		for _, p := range strings.Split(strings.ReplaceAll(fields_param, " ", ""), ",") {
			projection[p] = 1
		}
	}

	cursor, err := ads.Find(ctx, filter, options.Find().SetProjection(projection).SetSort(sort).SetSkip(offset).SetLimit(min(limit, max_limit)))
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
// GET /adbypage/page_id?offset=0&limit=0
func getAdsByPage(c *gin.Context) {
	id := c.Param("id")
	filter := bson.M{"page_id": id}
	sort := bson.M{"ad_creation_time": -1}
	returnAdList(c, filter, sort)
}

// Ads by creation date
// GET /adsbydate/date?offset=0&limit=0
func getAdsByDate(c *gin.Context) {
	date := c.Param("date")
	filter := bson.M{"ad_creation_time": date}
	returnAdList(c, filter, bson.M{})
}

// Search ads by page name
// GET /search/query?offset=0&limit=0
func searchByPage(c *gin.Context) {
	search := c.Param("search")
	filter := bson.M{"$text": bson.M{"$search": search}}
	sort := bson.M{"score": bson.M{"$meta": "textScore"}}
	returnAdList(c, filter, sort)
}

// Get lost ads
// GET /lostads?offset=0&limit=0
func getLostAds(c *gin.Context) {
	filter := bson.M{"lost": true}
	sort := bson.M{"ad_creation_time": -1}
	returnAdList(c, filter, sort)
}

// Get active ads
// GET /actives?offset=0&limit=0
func getActives(c *gin.Context) {
	filter := bson.M{"ad_delivery_start_time": bson.M{"$exists": true}, "ad_delivery_stop_time": nil}
	sort := bson.M{"ad_creation_time": -1}
	returnAdList(c, filter, sort)
}

// Get latest ads
// GET /latest
func getLatest(c *gin.Context) {
	filter := bson.M{}
	sort := bson.M{"$natural": -1}
	returnAdList(c, filter, sort)
}

// Queue an Ad to preview rendering
// POST /render_preview/id
func queuePreview(c *gin.Context) {
	ctx, cancel := context.WithTimeout(context.Background(), timeout*time.Second)
	defer cancel()
	id := c.Param("id")
	filter := bson.M{"_id": id}

	var result bson.M
	if err := ads.FindOne(ctx, filter).Decode(&result); err != nil {
		c.String(http.StatusNotFound, "Ad not found")
		return
	}
	insert := bson.M{"_id": id, "rendering_started": 0}
	_, err := render_queue.InsertOne(ctx, insert)
	if err != nil {
		c.String(http.StatusInternalServerError, "Ad already queued for rendering.")
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Queued ad for rendering. It should be ready in a few seconds."})
}

// Json response from the Facebook debug_token endpoint
type DEBUG_TOKEN_DATA struct {
	App_id     string `json:"app_id"`
	Expires_at int64  `json:"expires_at"`
	Is_valid   bool   `json:"is_valid"`
}

type DEBUG_TOKEN struct {
	Data DEBUG_TOKEN_DATA `json:"data"`
}

// Validates the FB TOKEN
func validateFBToken(token string) (DEBUG_TOKEN_DATA, error) {
	var response DEBUG_TOKEN
	resp, err := http.Get("https://graph.facebook.com/debug_token?input_token=" + token + "&access_token=" + token)
	if err != nil {
		return response.Data, fmt.Errorf("validation request failed")
	}

	// Read Results
	defer resp.Body.Close()
	err = json.NewDecoder(resp.Body).Decode(&response)
	if err != nil {
		return response.Data, fmt.Errorf("failed to parse json")
	}
	if !response.Data.Is_valid {
		return response.Data, fmt.Errorf("facebook access token is invalid")
	}
	return response.Data, nil
}

// Validate FB Token capability to do ad_archive requests
func validateTokenCapa(token string) bool {
	res, err := http.Get("https://graph.facebook.com/ads_archive?access_token=" + token + "&search_terms=*&ad_reached_countries=US&ad_active_status=ALL&limit=1")
	return (err == nil && res.StatusCode == http.StatusOK)
}

type TOKEN_DATA struct {
	Token string `json:"token"`
}

// Add a new token to the token collection
// GET /addToken?token=ACCESS_TOKEN
func addToken(c *gin.Context) {
	ctx, cancel := context.WithTimeout(context.Background(), timeout*time.Second)
	defer cancel()

	var data TOKEN_DATA
	if c.ShouldBind(&data) != nil {
		c.String(http.StatusBadRequest, "Please provide a valid token.")
		return
	}
	token := data.Token

	// Validate FB Token
	res, err := validateFBToken(token)
	if err != nil {
		c.String(http.StatusBadRequest, err.Error())
		return
	}
	id := res.App_id
	expiresAt := res.Expires_at

	// Validate that this token is able to do ad_archive reqeusts (completed https://www.facebook.com/ID)
	if !validateTokenCapa(token) {
		c.String(http.StatusBadRequest, "Your token can't be used to access ads, have you validated your account? See https://www.facebook.com/ads/library/api/ for all the necessary steps.")
		return
	}

	filter := bson.M{"_id": id}
	update := bson.M{"$set": bson.M{"token": token, "expiresAt": time.Unix(expiresAt, 0)}, "$setOnInsert": bson.M{"freshAt": 0}}
	opts := options.Update().SetUpsert(true)

	_, err = tokens.UpdateOne(ctx, filter, update, opts)
	if err != nil {
		c.String(http.StatusInternalServerError, "Error adding token.")
		return
	}
	c.String(http.StatusOK, "Successfully Added token! Thanks!")
}

func main() {
	defer func() {
		client.Disconnect(context.Background())
	}()

	router := gin.Default()
	router.Use(cors.Default())

	router.StaticFile("/", "frontend.html")
	router.GET("/total", getTotalAds)
	//router.GET("/ad/:id", getAd)
	//router.GET("/adsbypage/:id", getAdsByPage)
	//router.GET("/adsbydate/:date", getAdsByDate)
	//router.GET("/search/:search", searchByPage)
	//router.GET("/lostads", getLostAds)
	//router.GET("/actives", getActives)
	//router.GET("/latest", getLatest)
	//router.POST("/render_preview/:id", queuePreview)
	router.POST("/addToken", addToken)

	router.Run()
}
