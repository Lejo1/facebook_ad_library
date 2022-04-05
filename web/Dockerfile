FROM golang:alpine AS builder

WORKDIR /app
COPY go.mod go.mod
COPY go.sum go.sum
COPY main.go main.go

RUN go get -d -v
RUN CGO_ENABLED=0 go build -o /go/bin/app

FROM scratch
COPY --from=builder /go/bin/app /go/bin/app
COPY frontend.html .

ENTRYPOINT ["/go/bin/app"]
