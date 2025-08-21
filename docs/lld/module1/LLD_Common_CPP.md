# LLD Systems — C++ Ports

This Markdown contains C++ translations of your Java LLD files. Leading source comments are preserved verbatim above each ported code block.

## Table of Contents
1. [Parking Lot](#parking-lot)
2. [Movie Booking](#movie-booking)
3. [Food Delivery](#food-delivery)
4. [Ride Sharing](#ride-sharing)
5. [Chat App](#chat-app)
6. [File Store](#file-store)
7. [Instagram Feed](#instagram-feed)
8. [Meeting Scheduler](#meeting-scheduler)

## Parking Lot

```
/*
Template ->
1) define functional requirements
   - Single lot with levels, slots typed by vehicle (BIKE/CAR).
   - Entry: allocate nearest free slot by type, create ticket.
   - Exit: compute fee (base + hourly rounded up), release slot.
   - Query: availability per level & type.
   - Keep it concurrency-safe (basic locking), in-memory only.

2) define entities / actors
   Actors: Driver, Gate (Entry/Exit)
   Entities: Lot, Level, Slot(OPEN/OCCUPIED/MAINTENANCE, vehicleType), Ticket(OPEN/CLOSED), PricingRule

3) define apis - get/post/put, request, response
   GET  /availability?lotId=... -> { levelId -> {CAR:n, BIKE:n} }
   POST /entry                  {lotId, gateId, vehicleType, plate} -> {ticketId, slotId, entryAt}
   POST /exit                   {ticketId} -> {amount, exitAt, status}
   (Implemented as method calls in the Controller facade)

4) define services involved
   SlotService   - allocate/release slots (nearest level first)
   TicketService - issue/close tickets, orchestrates pricing + slot ops
   PricingService- compute amount (base + hourly)
   AvailabilityService - compute free counts excluding OCCUPIED/MAINTENANCE

5) define db schema - what all tables are required, what are the columns, what are the keys
   (In-memory for interview; relational sketch)
   lot(id PK, name, tz)
   level(id PK, lot_id FK, idx, name)
   slot(id PK, level_id FK, code UNIQUE(level_id, code), vehicle_type, status)
   pricing_rule(id PK, lot_id FK, vehicle_type, base_fee, hourly_rate)
   ticket(id PK, lot_id FK, slot_id FK, vehicle_type, plate, entry_at, exit_at, amount, status)
*/
```

### C++ Implementation

```cpp
#include <bits/stdc++.h>
using namespace std;
/*
Template ->
1) define functional requirements
   - Single lot with levels, slots typed by vehicle (BIKE/CAR).
   - Entry: allocate nearest free slot by type, create ticket.
   - Exit: compute fee (base + hourly rounded up), release slot.
   - Query: availability per level & type.
   - Keep it concurrency-safe (basic locking), in-memory only.

2) define entities / actors
   Actors: Driver, Gate (Entry/Exit)
   Entities: Lot, Level, Slot(OPEN/OCCUPIED/MAINTENANCE, vehicleType), Ticket(OPEN/CLOSED), PricingRule

3) define apis - get/post/put, request, response
   GET  /availability?lotId=... -> { levelId -> {CAR:n, BIKE:n} }
   POST /entry                  {lotId, gateId, vehicleType, plate} -> {ticketId, slotId, entryAt}
   POST /exit                   {ticketId} -> {amount, exitAt, status}
   (Implemented as method calls in the Controller facade)

4) define services involved
   SlotService   - allocate/release slots (nearest level first)
   TicketService - issue/close tickets, orchestrates pricing + slot ops
   PricingService- compute amount (base + hourly)
   AvailabilityService - compute free counts excluding OCCUPIED/MAINTENANCE

5) define db schema - what all tables are required, what are the columns, what are the keys
   (In-memory for interview; relational sketch)
   lot(id PK, name, tz)
   level(id PK, lot_id FK, idx, name)
   slot(id PK, level_id FK, code UNIQUE(level_id, code), vehicle_type, status)
   pricing_rule(id PK, lot_id FK, vehicle_type, base_fee, hourly_rate)
   ticket(id PK, lot_id FK, slot_id FK, vehicle_type, plate, entry_at, exit_at, amount, status)
*/
/* ===== Domain ===== */
enum VehicleType { BIKE, CAR }
enum SlotStatus   { OPEN, OCCUPIED, MAINTENANCE }
enum TicketStatus { OPEN, CLOSED }

const class Lot { const std::string id, name; const ZoneId zone; Lot(std::string i,std::string n,ZoneId z){id=i;name=n;zone=z;} }
const class Level { const std::string id, lotId, name; const int idx; Level(std::string i,std::string l,std::string n,int x){id=i;lotId=l;name=n;idx=x;} }
const class Slot {
    const std::string id, levelId, code; const VehicleType type; volatile SlotStatus status=SlotStatus.OPEN;
    Slot(std::string i,std::string lvl,std::string c,VehicleType t){id=i;levelId=lvl;code=c;type=t;}
}
const class PricingRule {
    const std::string id, lotId; const VehicleType type; const double baseFee, hourlyRate;
    PricingRule(std::string i,std::string l,VehicleType t,double b,double h){id=i;lotId=l;type=t;baseFee=b;hourlyRate=h;}
}
const class Ticket {
    const std::string id, lotId, slotId, plate; const VehicleType type; const Instant entryAt;
    volatile Instant exitAt; volatile double amount; volatile TicketStatus status=TicketStatus.OPEN;
    Ticket(std::string i,std::string l,std::string s,VehicleType t,std::string p,Instant e){id=i;lotId=l;slotId=s;type=t;plate=p;entryAt=e;}
}

/* ===== Simple Repos (in-memory) ===== */
class Ids { const AtomicLong seq=new AtomicLong(1); std::string next(std::string p){return p+"-"+seq.getAndIncrement();} }
class LotsRepo { const std::unordered_map<std::string,Lot> m=new ConcurrentHashMap<>(); Lot save(Lot x){m.put(x.id,x);return x;} std::optional<Lot> byId(std::string id){return Optional.ofNullable(m.get(id));} }
class LevelsRepo { const std::unordered_map<std::string,Level> m=new ConcurrentHashMap<>(); Level save(Level x){m.put(x.id,x);return x;} std::vector<Level> byLot(std::string lotId){return m.values().stream().filter(a->a.lotId == (lotId)).sorted(Comparator.comparingInt(a->a.idx)).collect(Collectors.toList());} }
class SlotsRepo {
    const std::unordered_map<std::string,Slot> m=new ConcurrentHashMap<>();
    Slot save(Slot x){m.put(x.id,x);return x;}
    std::optional<Slot> byId(std::string id){return Optional.ofNullable(m.get(id));}
    std::vector<Slot> byLevel(std::string levelId){return m.values().stream().filter(s->s.levelId == (levelId)).collect(Collectors.toList());}
}
class PricingRepo {
    const std::unordered_map<std::string,PricingRule> m=new ConcurrentHashMap<>();
    PricingRule save(PricingRule p){m.put(p.id,p);return p;}
    std::optional<PricingRule> byLotType(std::string lotId, VehicleType t){return m.values().stream().filter(r->r.lotId == (lotId)&&r.type==t).findFirst();}
}
class TicketsRepo {
    const std::unordered_map<std::string,Ticket> m=new ConcurrentHashMap<>();
    Ticket save(Ticket t){m.put(t.id,t);return t;}
    std::optional<Ticket> byId(std::string id){return Optional.ofNullable(m.get(id));}
}

/* ===== Exceptions ===== */
class DomainException extends RuntimeException { DomainException(std::string m){super(m);} }

/* ===== Services ===== */
class PricingService {
    const PricingRepo pricing; const LotsRepo lots;
    PricingService(PricingRepo p, LotsRepo l){pricing=p;lots=l;}
    double compute(std::string lotId, VehicleType type, Instant entry, Instant exit){
        PricingRule r = pricing.byLotType(lotId, type).orElseThrow(()->new DomainException("pricing missing"));
        long secs = Math.max(0, Duration.between(entry, exit).getSeconds());
        long hrs = (secs==0)?0:((secs+3599)/3600); // round up started hour
        double total = r.baseFee + r.hourlyRate * hrs;
        return Math.round(total*100.0)/100.0;
    }
}
class SlotService {
    const SlotsRepo slots; const LevelsRepo levels;
    SlotService(SlotsRepo s, LevelsRepo l){slots=s;levels=l;}
    synchronized Slot allocateNearest(std::string lotId, VehicleType type){
        for (Level lvl: levels.byLot(lotId)){
            for (Slot s: slots.byLevel(lvl.id)){
                if (s.type==type && s.status==SlotStatus.OPEN){
                    s.status=SlotStatus.OCCUPIED; return slots.save(s);
                }
            }
        }
        throw new DomainException("no free slot");
    }
    synchronized void release(std::string slotId){
        Slot s = slots.byId(slotId).orElseThrow(()->new DomainException("slot not found"));
        s.status=SlotStatus.OPEN; slots.save(s);
    }
}
class TicketService {
    const TicketsRepo tickets; const SlotService slotSvc; const PricingService pricingSvc; const Ids ids;
    TicketService(TicketsRepo t, SlotService s, PricingService p, Ids ids){tickets=t;slotSvc=s;pricingSvc=p;this->ids=ids;}
    Ticket entry(std::string lotId, VehicleType type, std::string plate){
        Slot s = slotSvc.allocateNearest(lotId, type);
        Ticket t = new Ticket(ids.next("tkt"), lotId, s.id, type, plate, Instant.now());
        return tickets.save(t);
    }
    Ticket exit(std::string ticketId){
        Ticket t = tickets.byId(ticketId).orElseThrow(()->new DomainException("ticket not found"));
        if (t.status==TicketStatus.CLOSED) return t;
        t.exitAt = Instant.now();
        t.amount = pricingSvc.compute(t.lotId, t.type, t.entryAt, t.exitAt);
        t.status = TicketStatus.CLOSED;
        tickets.save(t);
        slotSvc.release(t.slotId);
        return t;
    }
}
class AvailabilityService {
    const LevelsRepo levels; const SlotsRepo slots;
    AvailabilityService(LevelsRepo l, SlotsRepo s){levels=l;slots=s;}
    std::unordered_map<std::string, std::unordered_map<VehicleType,int>> availability(std::string lotId){
        std::unordered_map<std::string,std::unordered_map<VehicleType,int>> out = std::unordered_map<>{};
        for (Level lvl: levels.byLot(lotId)){
            EnumMap<VehicleType,int> m = new EnumMap<>(VehicleType.class);
            for (VehicleType vt: VehicleType.values()) m.put(vt,0);
            for (Slot s: slots.byLevel(lvl.id)){
                if (s.status==SlotStatus.OPEN) m.compute(s.type,(k,v)->v+1);
            }
            out.put(lvl.name, m);
        }
        return out;
    }
}

/* ===== Controller (facade mirroring APIs) ===== */
class ParkingController {
    const AvailabilityService avail; const TicketService tickets;
    ParkingController(AvailabilityService a, TicketService t){avail=a;tickets=t;}
    std::unordered_map<std::string, std::unordered_map<VehicleType,int>> getAvailability(std::string lotId){ return avail.availability(lotId); }
    Ticket postEntry(std::string lotId, VehicleType type, std::string plate){ return tickets.entry(lotId, type, plate); }
    Ticket postExit(std::string ticketId){ return tickets.exit(ticketId); }
}

/* ===== Bootstrap / Demo (kept tiny for 40-min scope) ===== */
class ParkingLot40Min {
    int main() {
        Ids ids = new Ids();
        // Repos
        LotsRepo lots = new LotsRepo();
        LevelsRepo levels = new LevelsRepo();
        SlotsRepo slots = new SlotsRepo();
        PricingRepo pricing = new PricingRepo();
        TicketsRepo tickets = new TicketsRepo();

        // Seed a small lot
        Lot lot = lots.save(new Lot("LOT-1","HSR Central", ZoneId.of("Asia/Kolkata")));
        Level L0 = levels.save(new Level("L0","LOT-1","Ground",0));
        Level L1 = levels.save(new Level("L1","LOT-1","P1",1));
        // Few slots
        slots.save(new Slot("S1","L0","C-001",VehicleType.CAR));
        slots.save(new Slot("S2","L0","C-002",VehicleType.CAR));
        slots.save(new Slot("S3","L1","B-001",VehicleType.BIKE));
        // Pricing
        pricing.save(new PricingRule("PR-CAR","LOT-1",VehicleType.CAR,  20.0, 30.0));
        pricing.save(new PricingRule("PR-BIKE","LOT-1",VehicleType.BIKE, 10.0, 10.0));

        // Services + Controller
        PricingService pricingSvc = new PricingService(pricing, lots);
        SlotService slotSvc = new SlotService(slots, levels);
        TicketService ticketSvc = new TicketService(tickets, slotSvc, pricingSvc, ids);
        AvailabilityService av = new AvailabilityService(levels, slots);
        ParkingController api = new ParkingController(av, ticketSvc);

        // --- Demo as API calls ---
        std::cout << "GET /availability -> " + api.getAvailability("LOT-1")) << std::endl;
        Ticket t1 = api.postEntry("LOT-1", VehicleType.CAR, "KA-01-AB-1234");
        std::cout << "POST /entry -> " + t1.id + " slot=" + t1.slotId) << std::endl;
        std::cout << "GET /availability -> " + api.getAvailability("LOT-1")) << std::endl;
        sleep(1200); // simulate time
        Ticket closed = api.postExit(t1.id);
        std::cout << "POST /exit -> ticket=" + closed.id + " amount=" + closed.amount) << std::endl;
        std::cout << "GET /availability -> " + api.getAvailability("LOT-1")) << std::endl;
    }
    static void sleep(long ms){ try{ Thread.sleep(ms);}catch(Exception ignored){} }
}
```

## Movie Booking

```
/*
Template ->
1) define functional requirements
   - Browse shows for a movie in a city & date.
   - View seat map for a show: FREE / HELD (by TTL hold) / BOOKED.
   - Hold seats with TTL (e.g., 5 minutes). Holds block others but auto-expire on read.
   - Confirm booking from a valid hold; mark seats BOOKED; compute price.
   - Confirm payment (stub), return e-ticket code.
   - In-memory only, concurrency-safe per Show (locks). Keep it 40-min friendly.

2) define entities / actors
   Actors: User, System (Seat Inventory), Payment Gateway (stub)
   Entities: Movie, Theater, Screen, Seat, Show, SeatHold, Booking, Payment

3) define apis - get/post/put, request, response
   GET  /movies/{movieId}/shows?city=...&date=YYYY-MM-DD
        -> [{showId, theater, screen, startAt, basePrice}]
   GET  /shows/{showId}/seats
        -> { showId, seats: [{seatId,row,col,type,status:FREE|HELD|BOOKED}], holdTtlSec }
   POST /shows/{showId}/hold
        { userId, seatIds:[...], ttlSec }
        -> { holdId, expiresAt }
   POST /bookings
        { holdId, userId }
        -> { bookingId, amount, seats:[...], qr }
   POST /payments/confirm
        { bookingId, method, txnRef? }
        -> { paymentId, status }

4) define services involved
   ShowSearchService     - list shows for movie/city/date.
   SeatInventoryService  - seat map, create hold (per-show lock), check expiries.
   BookingService        - confirm booking from hold (per-show lock), pricing.
   PaymentService        - stub payment confirmation.
   IdGenerator           - simple IDs.

5) define db schema - what all tables are required, what are the columns, what are the keys
   movie(id PK, title, duration_min)
   theater(id PK, city, name)
   screen(id PK, theater_id FK, name, rows, cols)
   seat(id PK, screen_id FK, row, col, type ENUM)
   show(id PK, movie_id FK, screen_id FK, start_at, base_price NUM, status)
   seat_hold(id PK, show_id FK, user_id, seat_ids JSON, expires_at, active)
      INDEX(show_id, active, expires_at)
   booking(id PK, show_id FK, user_id, seat_ids JSON, amount NUM, status, qr)
      INDEX(show_id, status)
   payment(id PK, booking_id FK UNIQUE, method, amount NUM, status, txn_ref, paid_at)
*/
```

### C++ Implementation

```cpp
#include <bits/stdc++.h>
using namespace std;
/*
Template ->
1) define functional requirements
   - Browse shows for a movie in a city & date.
   - View seat map for a show: FREE / HELD (by TTL hold) / BOOKED.
   - Hold seats with TTL (e.g., 5 minutes). Holds block others but auto-expire on read.
   - Confirm booking from a valid hold; mark seats BOOKED; compute price.
   - Confirm payment (stub), return e-ticket code.
   - In-memory only, concurrency-safe per Show (locks). Keep it 40-min friendly.

2) define entities / actors
   Actors: User, System (Seat Inventory), Payment Gateway (stub)
   Entities: Movie, Theater, Screen, Seat, Show, SeatHold, Booking, Payment

3) define apis - get/post/put, request, response
   GET  /movies/{movieId}/shows?city=...&date=YYYY-MM-DD
        -> [{showId, theater, screen, startAt, basePrice}]
   GET  /shows/{showId}/seats
        -> { showId, seats: [{seatId,row,col,type,status:FREE|HELD|BOOKED}], holdTtlSec }
   POST /shows/{showId}/hold
        { userId, seatIds:[...], ttlSec }
        -> { holdId, expiresAt }
   POST /bookings
        { holdId, userId }
        -> { bookingId, amount, seats:[...], qr }
   POST /payments/confirm
        { bookingId, method, txnRef? }
        -> { paymentId, status }

4) define services involved
   ShowSearchService     - list shows for movie/city/date.
   SeatInventoryService  - seat map, create hold (per-show lock), check expiries.
   BookingService        - confirm booking from hold (per-show lock), pricing.
   PaymentService        - stub payment confirmation.
   IdGenerator           - simple IDs.

5) define db schema - what all tables are required, what are the columns, what are the keys
   movie(id PK, title, duration_min)
   theater(id PK, city, name)
   screen(id PK, theater_id FK, name, rows, cols)
   seat(id PK, screen_id FK, row, col, type ENUM)
   show(id PK, movie_id FK, screen_id FK, start_at, base_price NUM, status)
   seat_hold(id PK, show_id FK, user_id, seat_ids JSON, expires_at, active)
      INDEX(show_id, active, expires_at)
   booking(id PK, show_id FK, user_id, seat_ids JSON, amount NUM, status, qr)
      INDEX(show_id, status)
   payment(id PK, booking_id FK UNIQUE, method, amount NUM, status, txn_ref, paid_at)
*/
/* ===== Enums ===== */
enum SeatType { REGULAR, PREMIUM }
enum BookingStatus { PENDING, CONFIRMED, CANCELLED }
enum PaymentStatus { PENDING, PAID, FAILED }

/* ===== Domain ===== */
const class Movie { const std::string id, title; const int durationMin; Movie(std::string id,std::string title,int d){this->id=id;this->title=title;this->durationMin=d;} }
const class Theater { const std::string id, city, name; Theater(std::string id,std::string city,std::string name){this->id=id;this->city=city;this->name=name;} }
const class Screen { const std::string id, theaterId, name; const int rows, cols; Screen(std::string id,std::string th,std::string name,int r,int c){this->id=id;this->theaterId=th;this->name=name;this->rows=r;this->cols=c;} }
const class Seat { const std::string id, screenId; const int row, col; const SeatType type; Seat(std::string id,std::string sid,int r,int c,SeatType t){this->id=id;this->screenId=sid;this->row=r;this->col=c;this->type=t;} }
const class Show { const std::string id, movieId, screenId; const ZonedDateTime startAt; const double basePrice; Show(std::string id,std::string mid,std::string sc,ZonedDateTime t,double p){this->id=id;this->movieId=mid;this->screenId=sc;this->startAt=t;this->basePrice=p;} }

const class SeatHold {
    const std::string id, showId, userId; const std::unordered_set<std::string> seatIds;
    const Instant expiresAt; volatile boolean active=true;
    SeatHold(std::string id,std::string showId,std::string userId,std::unordered_set<std::string> seatIds,Instant exp){this->id=id;this->showId=showId;this->userId=userId;this->seatIds=seatIds;this->expiresAt=exp;}
}

const class Booking {
    const std::string id, showId, userId, qr;
    const std::unordered_set<std::string> seatIds;
    const double amount; volatile BookingStatus status=BookingStatus.CONFIRMED;
    Booking(std::string id,std::string showId,std::string userId,std::unordered_set<std::string> seatIds,double amount,std::string qr){
        this->id=id;this->showId=showId;this->userId=userId;this->seatIds=seatIds;this->amount=amount;this->qr=qr;
    }
}

const class Payment {
    const std::string id, bookingId, method, txnRef; const double amount;
    volatile PaymentStatus status=PaymentStatus.PENDING; volatile Instant paidAt;
    Payment(std::string id,std::string b,std::string m,std::string x,double a){this->id=id;this->bookingId=b;this->method=m;this->txnRef=x;this->amount=a;}
}

/* ===== Repos (in-memory) ===== */
class Ids { const AtomicLong n=new AtomicLong(1); std::string next(std::string p){ return p+"-"+n.getAndIncrement(); } }

class MoviesRepo { const std::unordered_map<std::string,Movie> m=new ConcurrentHashMap<>(); Movie save(Movie x){m.put(x.id,x);return x;} std::optional<Movie> byId(std::string id){return Optional.ofNullable(m.get(id));} }
class TheatersRepo { const std::unordered_map<std::string,Theater> m=new ConcurrentHashMap<>(); Theater save(Theater x){m.put(x.id,x);return x;} std::optional<Theater> byId(std::string id){return Optional.ofNullable(m.get(id));} }
class ScreensRepo { const std::unordered_map<std::string,Screen> m=new ConcurrentHashMap<>(); Screen save(Screen x){m.put(x.id,x);return x;} std::optional<Screen> byId(std::string id){return Optional.ofNullable(m.get(id));} }
class SeatsRepo {
    const std::unordered_map<std::string,Seat> m=new ConcurrentHashMap<>();
    Seat save(Seat s){m.put(s.id,s);return s;}
    std::vector<Seat> byScreen(std::string screenId){ return m.values().stream().filter(s->s.screenId == (screenId)).collect(Collectors.toList()); }
    std::optional<Seat> byId(std::string id){return Optional.ofNullable(m.get(id));}
}
class ShowsRepo { const std::unordered_map<std::string,Show> m=new ConcurrentHashMap<>(); Show save(Show x){m.put(x.id,x);return x;} std::optional<Show> byId(std::string id){return Optional.ofNullable(m.get(id));} std::vector<Show> all(){return new std::vector<>(m.values());} }
class HoldsRepo {
    const std::unordered_map<std::string,SeatHold> m=new ConcurrentHashMap<>();
    SeatHold save(SeatHold h){m.put(h.id,h);return h;}
    std::optional<SeatHold> byId(std::string id){return Optional.ofNullable(m.get(id));}
    std::vector<SeatHold> activeByShow(std::string showId){
        Instant now=Instant.now();
        return m.values().stream().filter(h->h.showId == (showId)&&h.active&&h.expiresAt.isAfter(now)).collect(Collectors.toList());
    }
}
class BookingsRepo {
    const std::unordered_map<std::string,Booking> m=new ConcurrentHashMap<>();
    Booking save(Booking b){m.put(b.id,b);return b;}
    std::vector<Booking> byShow(std::string showId){ return m.values().stream().filter(b->b.showId == (showId)&&b.status==BookingStatus.CONFIRMED).collect(Collectors.toList()); }
}
class PaymentsRepo {
    const std::unordered_map<std::string,Payment> m=new ConcurrentHashMap<>();
    Payment save(Payment p){m.put(p.id,p);return p;}
    std::optional<Payment> byBooking(std::string bookingId){ return m.values().stream().filter(p->p.bookingId == (bookingId)).findFirst(); }
}

/* ===== Errors ===== */
class DomainException extends RuntimeException { DomainException(std::string m){super(m);} }

/* ===== Services ===== */
class ShowSearchService {
    const ShowsRepo shows; const TheatersRepo theaters;
    ShowSearchService(ShowsRepo s, TheatersRepo t){shows=s;theaters=t;}
    std::vector<Show> list(std::string movieId, std::string city, LocalDate date){
        return shows.all().stream()
                .filter(sh->sh.movieId == (movieId))
                .filter(sh->theaters.byId(sh.screenId.split(":")[0]).map(th->th.city.equalsIgnoreCase(city)).orElse(true))
                .filter(sh->sh.startAt.toLocalDate() == (date))
                .collect(Collectors.toList());
    }
}

class PerShowLocks {
    const ConcurrentHashMap<std::string, ReentrantLock> locks = new ConcurrentHashMap<>();
    ReentrantLock lockFor(std::string showId){ return locks.computeIfAbsent(showId, k->new ReentrantLock(true)); }
}

class SeatInventoryService {
    const ShowsRepo shows; const ScreensRepo screens; const SeatsRepo seats;
    const HoldsRepo holds; const BookingsRepo bookings; const PerShowLocks locks;

    SeatInventoryService(ShowsRepo sh,ScreensRepo sc,SeatsRepo se,HoldsRepo h,BookingsRepo b,PerShowLocks L){
        shows=sh; screens=sc; seats=se; holds=h; bookings=b; locks=L;
    }

    static const class SeatView {
        const std::string seatId; const int row, col; const SeatType type; const std::string status;
        SeatView(std::string id,int r,int c,SeatType t,std::string s){seatId=id;row=r;col=c;type=t;status=s;}
        std::string toString(){ return seatId+":"+status; }
    }

    std::vector<SeatView> seatMap(std::string showId){
        Show show = shows.byId(showId).orElseThrow(()->new DomainException("show not found"));
        Screen screen = screens.byId(show.screenId).orElseThrow(()->new DomainException("screen not found"));
        std::vector<Seat> allSeats = seats.byScreen(screen.id);
        std::unordered_set<std::string> booked = bookings.byShow(showId).stream().flatMap(b->b.seatIds.stream()).collect(Collectors.toSet());
        std::unordered_set<std::string> held = holds.activeByShow(showId).stream().flatMap(h->h.seatIds.stream()).collect(Collectors.toSet());
        std::vector<SeatView> out = std::vector<>{};
        for (Seat s: allSeats){
            std::string status = booked.contains(s.id) ? "BOOKED" : (held.contains(s.id) ? "HELD" : "FREE");
            out.add(new SeatView(s.id, s.row, s.col, s.type, status));
        }
        out.sort(Comparator.comparingInt((SeatView v)->v.row).thenComparingInt(v->v.col));
        return out;
    }

    SeatHold holdSeats(std::string showId, std::string userId, std::unordered_set<std::string> seatIds, Duration ttl){
        ReentrantLock lock = locks.lockFor(showId);
        lock.lock();
        try{
            // filter out expired automatically (holds.activeByShow uses time)
            std::unordered_set<std::string> booked = bookings.byShow(showId).stream().flatMap(b->b.seatIds.stream()).collect(Collectors.toSet());
            std::unordered_set<std::string> held = holds.activeByShow(showId).stream().flatMap(h->h.seatIds.stream()).collect(Collectors.toSet());

            // validate requested seats exist & are free
            for (std::string seatId: seatIds){
                if (booked.contains(seatId) || held.contains(seatId)) throw new DomainException("seat not available: "+seatId);
            }
            SeatHold h = new SeatHold(BookMyShow40Min.ids.next("hold"), showId, userId, seatIds, Instant.now().plus(ttl));
            return holds.save(h);
        } // finally { lock.unlock(); }
    }
}

class BookingService {
    const ShowsRepo shows; const HoldsRepo holds; const BookingsRepo bookings; const PaymentsRepo payments; const PerShowLocks locks;

    BookingService(ShowsRepo sh,HoldsRepo h,BookingsRepo b,PaymentsRepo p,PerShowLocks L){
        shows=sh; holds=h; bookings=b; payments=p; locks=L;
    }

    Booking confirm(std::string holdId){
        SeatHold h = holds.byId(holdId).orElseThrow(()->new DomainException("hold not found"));
        if (!h.active || h.expiresAt.isBefore(Instant.now())) throw new DomainException("hold expired");
        ReentrantLock lock = locks.lockFor(h.showId);
        lock.lock();
        try{
            // re-check availability under lock
            // (if any seat is already booked meanwhile, fail)
            // Collect currently booked seats for the show:
            std::unordered_set<std::string> booked = bookings.byShow(h.showId).stream().flatMap(b->b.seatIds.stream()).collect(Collectors.toSet());
            for (std::string s: h.seatIds) if (booked.contains(s)) throw new DomainException("seat got booked: "+s);

            Show show = shows.byId(h.showId).orElseThrow(()->new DomainException("show not found"));
            double price = show.basePrice * h.seatIds.size();
            std::string qr = UUID.randomUUID().toString();
            Booking b = new Booking(BookMyShow40Min.ids.next("bkg"), h.showId, h.userId, new std::unordered_set<>(h.seatIds), round2(price), qr);
            h.active = false; // consume hold
            return bookings.save(b);
        } // finally { lock.unlock(); }
    }

    static double round2(double v){ return Math.round(v*100.0)/100.0; }
}

class PaymentService {
    const PaymentsRepo payments;
    PaymentService(PaymentsRepo p){payments=p;}
    Payment confirm(std::string bookingId, double amount, std::string method, std::string txnRef){
        Payment pay = new Payment(BookMyShow40Min.ids.next("pay"), bookingId, method, txnRef, amount);
        pay.status = PaymentStatus.PAID; pay.paidAt = Instant.now(); // simulate success
        return payments.save(pay);
    }
}

/* ===== Controller Facade (mirrors the APIs) ===== */
class BookingController {
    const ShowSearchService search; const SeatInventoryService inv; const BookingService bookings; const PaymentService payments;

    BookingController(ShowSearchService s, SeatInventoryService i, BookingService b, PaymentService p){
        search=s; inv=i; bookings=b; payments=p;
    }

    std::vector<Show> getShows(std::string movieId, std::string city, LocalDate date){ return search.list(movieId, city, date); }

    std::vector<SeatInventoryService.SeatView> getSeatMap(std::string showId){ return inv.seatMap(showId); }

    SeatHold postHold(std::string showId, std::string userId, std::unordered_set<std::string> seatIds, long ttlSec){
        return inv.holdSeats(showId, userId, seatIds, Duration.ofSeconds(ttlSec));
    }

    Booking postBooking(std::string holdId){ return bookings.confirm(holdId); }

    Payment postPayment(std::string bookingId, double amount, std::string method, std::string txnRef){
        return payments.confirm(bookingId, amount, method, txnRef);
    }
}

/* ===== Bootstrap & Demo (tiny, 40-min compatible) ===== */
class BookMyShow40Min {
    static const Ids ids = new Ids();

    int main() {
        // Repos
        MoviesRepo movies = new MoviesRepo();
        TheatersRepo theaters = new TheatersRepo();
        ScreensRepo screens = new ScreensRepo();
        SeatsRepo seats = new SeatsRepo();
        ShowsRepo shows = new ShowsRepo();
        HoldsRepo holds = new HoldsRepo();
        BookingsRepo bookings = new BookingsRepo();
        PaymentsRepo payments = new PaymentsRepo();

        // Seed
        Movie m = movies.save(new Movie(ids.next("mov"), "Interstellar", 169));
        Theater th = theaters.save(new Theater("TH-1:SCR-1", "Bengaluru", "Galaxy Cinema"));
        Screen sc = screens.save(new Screen("SCR-1", th.id, "Screen 1", 3, 4)); // small 3x4 for demo
        // Seats
        for (int r=1;r<=sc.rows;r++){
            for (int c=1;c<=sc.cols;c++){
                SeatType type = (r==1?SeatType.PREMIUM:SeatType.REGULAR);
                seats.save(new Seat("SEAT-"+r+"-"+c, sc.id, r, c, type));
            }
        }
        // Show (note: we embed theater id in Show.screenId owner link for city mapping shortcut)
        ZonedDateTime start = ZonedDateTime.of(LocalDate.now(), LocalTime.of(19,0), ZoneId.of("Asia/Kolkata"));
        Show sh = shows.save(new Show(ids.next("show"), m.id, sc.id, start, 250.0));

        // Services
        PerShowLocks locks = new PerShowLocks();
        ShowSearchService search = new ShowSearchService(shows, theaters);
        SeatInventoryService inventory = new SeatInventoryService(shows, screens, seats, holds, bookings, locks);
        BookingService bookingSvc = new BookingService(shows, holds, bookings, payments, locks);
        PaymentService paymentSvc = new PaymentService(payments);

        // Controller
        BookingController api = new BookingController(search, inventory, bookingSvc, paymentSvc);

        // --- Demo flow (as API calls) ---
        std::cout << "GET /movies/{movieId}/shows?city=Bengaluru&date=today") << std::endl;
        std::cout << api.getShows(m.id, "Bengaluru", LocalDate.now())) << std::endl;

        std::cout << "\nGET /shows/{showId}/seats") << std::endl;
        std::cout << api.getSeatMap(sh.id)) << std::endl;

        std::cout << "\nPOST /shows/{showId}/hold  seats=[SEAT-1-1, SEAT-1-2]") << std::endl;
        SeatHold hold = api.postHold(sh.id, "user-42", setOf("SEAT-1-1","SEAT-1-2"), 300);
        std::cout << "Hold: "+hold.id+" expiresAt="+hold.expiresAt) << std::endl;

        std::cout << "\nGET /shows/{showId}/seats  (after hold)") << std::endl;
        std::cout << api.getSeatMap(sh.id)) << std::endl;

        std::cout << "\nPOST /bookings  {holdId}") << std::endl;
        Booking booking = api.postBooking(hold.id);
        std::cout << "Booking: "+booking.id+" seats="+booking.seatIds+" amount="+booking.amount+" qr="+booking.qr) << std::endl;

        std::cout << "\nPOST /payments/confirm") << std::endl;
        Payment pay = api.postPayment(booking.id, booking.amount, "UPI", "TXN-123");
        std::cout << "Payment: "+pay.id+" status="+pay.status+" paidAt="+pay.paidAt) << std::endl;

        std::cout << "\nGET /shows/{showId}/seats  (after booking)") << std::endl;
        std::cout << api.getSeatMap(sh.id)) << std::endl;
    }

    static std::unordered_set<std::string> setOf(std::string...xs){ return new std::unordered_set<>(Arrays.asList(xs)); }
}
```

## Food Delivery

```
/*
Template ->
1) define functional requirements
   - Browse restaurants by area/cuisine; view menu items (veg/non-veg).
   - Create cart per user per restaurant; add/remove items; compute totals, taxes, delivery fee.
   - Place order (from a single restaurant), capture address & instructions.
   - Payment confirmation (stub) → move order to PLACED/PAID.
   - Assign nearest available delivery partner; update order status (PREPARING → PICKED_UP → DELIVERED).
   - Track order with ETA; list user's past orders.
   - In-memory implementation; single city; thread-safe where needed; deliverable in ~40 min.

2) define entities / actors
   Actors: Customer, Restaurant, DeliveryPartner, System/PaymentGateway (stub)
   Entities: Restaurant, MenuItem, Cart, CartItem, Order, OrderItem, Payment, DeliveryPartner, GeoPoint

3) define apis - get/post/put, request, response  (mirrored by controller methods)
   GET  /restaurants?area=HSR&cuisine=NorthIndian     -> [restaurant...]
   GET  /restaurants/{id}/menu                        -> [menuItem...]
   POST /cart/items                                   {userId, restaurantId, itemId, qty} -> cart view
   DELETE /cart/items                                 {userId, itemId} -> cart view
   POST /orders                                       {userId, address, instructions?} -> {orderId, amount}
   POST /payments/confirm                             {orderId, method, txnRef?} -> {paymentId, status}
   POST /orders/{orderId}/assign                      -> {partnerId, etaMin}
   GET  /orders/{orderId}/track                       -> {status, etaMin, partnerLoc?}

4) define services involved
   CatalogService        - search restaurants, menu retrieval
   CartService           - add/remove, compute totals
   PricingService        - taxes (e.g., 5%), delivery fee (distance slab), surge hooks
   OrderService          - place & manage order lifecycle
   PaymentService        - confirm payments (stub)
   AssignmentService     - choose nearest available delivery partner
   TrackingService       - ETA calc & status updates
   IdGenerator           - ID generation

5) define db schema - what all tables are required, what are the columns, what are the keys
   restaurant(id PK, name, area, cuisines JSON, lat, lon, rating)
   menu_item(id PK, restaurant_id FK, name, price, veg BOOL, in_stock BOOL)
   cart(id PK, user_id, restaurant_id, updated_at)
   cart_item(id PK, cart_id FK, item_id FK, qty)
   order(id PK, user_id, restaurant_id, address, instructions, status, sub_total, tax, delivery_fee, total, created_at)
   order_item(id PK, order_id FK, item_id FK, name_snapshot, price_snapshot, qty)
   payment(id PK, order_id FK UNIQUE, method, amount, txn_ref, status, paid_at)
   delivery_partner(id PK, name, lat, lon, available BOOL, rating)
*/
```

### C++ Implementation

```cpp
#include <bits/stdc++.h>
using namespace std;
/*
Template ->
1) define functional requirements
   - Browse restaurants by area/cuisine; view menu items (veg/non-veg).
   - Create cart per user per restaurant; add/remove items; compute totals, taxes, delivery fee.
   - Place order (from a single restaurant), capture address & instructions.
   - Payment confirmation (stub) → move order to PLACED/PAID.
   - Assign nearest available delivery partner; update order status (PREPARING → PICKED_UP → DELIVERED).
   - Track order with ETA; list user's past orders.
   - In-memory implementation; single city; thread-safe where needed; deliverable in ~40 min.

2) define entities / actors
   Actors: Customer, Restaurant, DeliveryPartner, System/PaymentGateway (stub)
   Entities: Restaurant, MenuItem, Cart, CartItem, Order, OrderItem, Payment, DeliveryPartner, GeoPoint

3) define apis - get/post/put, request, response  (mirrored by controller methods)
   GET  /restaurants?area=HSR&cuisine=NorthIndian     -> [restaurant...]
   GET  /restaurants/{id}/menu                        -> [menuItem...]
   POST /cart/items                                   {userId, restaurantId, itemId, qty} -> cart view
   DELETE /cart/items                                 {userId, itemId} -> cart view
   POST /orders                                       {userId, address, instructions?} -> {orderId, amount}
   POST /payments/confirm                             {orderId, method, txnRef?} -> {paymentId, status}
   POST /orders/{orderId}/assign                      -> {partnerId, etaMin}
   GET  /orders/{orderId}/track                       -> {status, etaMin, partnerLoc?}

4) define services involved
   CatalogService        - search restaurants, menu retrieval
   CartService           - add/remove, compute totals
   PricingService        - taxes (e.g., 5%), delivery fee (distance slab), surge hooks
   OrderService          - place & manage order lifecycle
   PaymentService        - confirm payments (stub)
   AssignmentService     - choose nearest available delivery partner
   TrackingService       - ETA calc & status updates
   IdGenerator           - ID generation

5) define db schema - what all tables are required, what are the columns, what are the keys
   restaurant(id PK, name, area, cuisines JSON, lat, lon, rating)
   menu_item(id PK, restaurant_id FK, name, price, veg BOOL, in_stock BOOL)
   cart(id PK, user_id, restaurant_id, updated_at)
   cart_item(id PK, cart_id FK, item_id FK, qty)
   order(id PK, user_id, restaurant_id, address, instructions, status, sub_total, tax, delivery_fee, total, created_at)
   order_item(id PK, order_id FK, item_id FK, name_snapshot, price_snapshot, qty)
   payment(id PK, order_id FK UNIQUE, method, amount, txn_ref, status, paid_at)
   delivery_partner(id PK, name, lat, lon, available BOOL, rating)
*/
/* ===== Domain ===== */
enum OrderStatus { CART, PLACED, PAID, PREPARING, PICKED_UP, DELIVERED, CANCELLED }
enum PaymentStatus { PENDING, PAID, FAILED }

const class GeoPoint { const double lat, lon; GeoPoint(double lat,double lon){this->lat=lat;this->lon=lon;} }
const class Restaurant {
    const std::string id, name, area; const std::vector<std::string> cuisines; const GeoPoint loc; const double rating;
    Restaurant(std::string id,std::string name,std::string area,std::vector<std::string> cuisines,GeoPoint loc,double rating){
        this->id=id; this->name=name; this->area=area; this->cuisines=cuisines; this->loc=loc; this->rating=rating;
    }
}
const class MenuItem {
    const std::string id, restaurantId, name; const double price; const boolean veg; volatile boolean inStock;
    MenuItem(std::string id,std::string rid,std::string name,double price,boolean veg,boolean inStock){
        this->id=id; this->restaurantId=rid; this->name=name; this->price=price; this->veg=veg; this->inStock=inStock;
    }
}

const class CartItem { const std::string itemId; int qty; CartItem(std::string itemId,int qty){this->itemId=itemId; this->qty=qty;} }
const class Cart {
    const std::string id, userId, restaurantId; const std::unordered_map<std::string,CartItem> items = std::unordered_map<>{};
    volatile Instant updatedAt = Instant.now();
    Cart(std::string id,std::string userId,std::string restaurantId){this->id=id; this->userId=userId; this->restaurantId=restaurantId;}
}

const class OrderItem {
    const std::string itemId, nameSnapshot; const double priceSnapshot; const int qty;
    OrderItem(std::string itemId,std::string name,double price,int qty){this->itemId=itemId;this->nameSnapshot=name;this->priceSnapshot=price;this->qty=qty;}
}
const class Order {
    const std::string id, userId, restaurantId, address, instructions;
    const std::vector<OrderItem> items;
    volatile OrderStatus status = OrderStatus.PLACED;
    const double subTotal, tax, deliveryFee, total;
    volatile Instant createdAt = Instant.now();
    volatile std::string partnerId; volatile int etaMin;
    Order(std::string id,std::string userId,std::string restaurantId,std::string address,std::string instr,std::vector<OrderItem> items,
          double sub,double tax,double del,double tot){
        this->id=id;this->userId=userId;this->restaurantId=restaurantId;this->address=address;this->instructions=instr;this->items=items;
        this->subTotal=sub; this->tax=tax; this->deliveryFee=del; this->total=tot;
    }
}

const class Payment {
    const std::string id, orderId, method, txnRef; const double amount;
    volatile PaymentStatus status = PaymentStatus.PENDING; volatile Instant paidAt;
    Payment(std::string id,std::string orderId,std::string method,std::string txnRef,double amount){
        this->id=id; this->orderId=orderId; this->method=method; this->txnRef=txnRef; this->amount=amount;
    }
}

const class DeliveryPartner {
    const std::string id, name; volatile GeoPoint loc; volatile boolean available; const double rating;
    DeliveryPartner(std::string id,std::string name,GeoPoint loc,boolean available,double rating){
        this->id=id; this->name=name; this->loc=loc; this->available=available; this->rating=rating;
    }
}

/* ===== Repos (in-memory) ===== */
class Ids { const AtomicLong n=new AtomicLong(1); std::string next(std::string p){return p+"-"+n.getAndIncrement();} }

class RestaurantRepo {
    const std::unordered_map<std::string,Restaurant> m=new ConcurrentHashMap<>();
    Restaurant save(Restaurant r){m.put(r.id,r);return r;}
    std::vector<Restaurant> search(std::string area,std::string cuisine){
        return m.values().stream()
                .filter(r->area==nullptr||r.area.equalsIgnoreCase(area))
                .filter(r->cuisine==nullptr||r.cuisines.stream().anyMatch(c->c.equalsIgnoreCase(cuisine)))
                .sorted(Comparator.comparingDouble((Restaurant r)->-r.rating))
                .collect(Collectors.toList());
    }
    std::optional<Restaurant> byId(std::string id){ return Optional.ofNullable(m.get(id)); }
}
class MenuRepo {
    const std::unordered_map<std::string,MenuItem> m=new ConcurrentHashMap<>();
    MenuItem save(MenuItem x){m.put(x.id,x);return x;}
    std::vector<MenuItem> byRestaurant(std::string rid){ return m.values().stream().filter(i->i.restaurantId == (rid)).collect(Collectors.toList()); }
    std::optional<MenuItem> byId(std::string id){ return Optional.ofNullable(m.get(id)); }
}
class CartRepo {
    const std::unordered_map<std::string,Cart> m=new ConcurrentHashMap<>(); // key: userId
    Cart save(Cart c){ m.put(c.userId, c); return c; }
    std::optional<Cart> byUser(std::string userId){ return Optional.ofNullable(m.get(userId)); }
    void delete(std::string userId){ m.remove(userId); }
}
class OrderRepo {
    const std::unordered_map<std::string,Order> m=new ConcurrentHashMap<>();
    Order save(Order o){ m.put(o.id,o); return o; }
    std::optional<Order> byId(std::string id){ return Optional.ofNullable(m.get(id)); }
    std::vector<Order> byUser(std::string user){ return m.values().stream().filter(o->o.userId == (user)).collect(Collectors.toList()); }
}
class PaymentRepo {
    const std::unordered_map<std::string,Payment> m=new ConcurrentHashMap<>();
    Payment save(Payment p){ m.put(p.id,p); return p; }
    std::optional<Payment> byOrder(std::string orderId){ return m.values().stream().filter(x->x.orderId == (orderId)).findFirst(); }
}
class PartnerRepo {
    const std::unordered_map<std::string,DeliveryPartner> m=new ConcurrentHashMap<>();
    DeliveryPartner save(DeliveryPartner p){ m.put(p.id,p); return p; }
    std::vector<DeliveryPartner> available(){ return m.values().stream().filter(p->p.available).collect(Collectors.toList()); }
    std::optional<DeliveryPartner> byId(std::string id){ return Optional.ofNullable(m.get(id)); }
}

/* ===== Utils ===== */
class Haversine {
    static double distanceKm(GeoPoint a, GeoPoint b){
        double R=6371.0, dLat=Math.toRadians(b.lat-a.lat), dLon=Math.toRadians(b.lon-a.lon);
        double s1=Math.sin(dLat/2), s2=Math.sin(dLon/2);
        double aa=s1*s1 + Math.cos(Math.toRadians(a.lat))*Math.cos(Math.toRadians(b.lat))*s2*s2;
        return 2*R*Math.asin(Math.sqrt(aa));
    }
    static int etaMin(double km){ return Math.max(6, (int)Math.round(km/0.35)); } // ~21 km/h avg
}
class DomainException extends RuntimeException { DomainException(std::string m){super(m);} }

/* ===== Services ===== */
class CatalogService {
    const RestaurantRepo restaurants; const MenuRepo menu;
    CatalogService(RestaurantRepo r, MenuRepo m){restaurants=r; menu=m;}
    std::vector<Restaurant> search(std::string area,std::string cuisine){ return restaurants.search(area, cuisine); }
    std::vector<MenuItem> menu(std::string restaurantId){ return menu.byRestaurant(restaurantId); }
}
class PricingService {
    const double taxRate = 0.05; // 5%
    double subTotal(std::vector<OrderItem> items){ return round2(items.stream().mapToDouble(i->i.priceSnapshot*i.qty).sum()); }
    double tax(double sub){ return round2(sub * taxRate); }
    double deliveryFee(double distanceKm){
        double fee = distanceKm<=2 ? 20 : (distanceKm<=5 ? 35 : 50 + (distanceKm-5)*5);
        return round2(fee);
    }
    double total(double sub,double tax,double del){ return round2(sub+tax+del); }
    static double round2(double v){ return Math.round(v*100.0)/100.0; }
}
class CartService {
    const CartRepo carts; const MenuRepo menu; const Ids ids;
    CartService(CartRepo c, MenuRepo m, Ids ids){carts=c;menu=m;this->ids=ids;}
    synchronized Cart addItem(std::string userId, std::string restaurantId, std::string itemId, int qty){
        MenuItem mi = menu.byId(itemId).orElseThrow(()->new DomainException("item not found"));
        if (!mi.inStock) throw new DomainException("item out of stock");
        Cart cart = carts.byUser(userId).orElse(nullptr);
        if (cart==nullptr) cart = carts.save(new Cart(ids.next("cart"), userId, restaurantId));
        if (!cart.restaurantId == (restaurantId)) throw new DomainException("cart restricted to 1 restaurant");
        CartItem ci = cart.items.getOrDefault(itemId, new CartItem(itemId,0));
        ci.qty += qty;
        if (ci.qty<=0) cart.items.remove(itemId); else cart.items.put(itemId, ci);
        cart.updatedAt = Instant.now();
        return carts.save(cart);
    }
    synchronized Cart removeItem(std::string userId, std::string itemId){
        Cart cart = carts.byUser(userId).orElseThrow(()->new DomainException("cart not found"));
        cart.items.remove(itemId);
        cart.updatedAt = Instant.now();
        return carts.save(cart);
    }
    synchronized void clear(std::string userId){ carts.delete(userId); }
}
class OrderService {
    const OrderRepo orders; const CartRepo carts; const MenuRepo menu; const PricingService pricing; const RestaurantRepo restaurants; const Ids ids;
    OrderService(OrderRepo o, CartRepo c, MenuRepo m, PricingService p, RestaurantRepo r, Ids ids){
        orders=o;carts=c;menu=m;pricing=p;restaurants=r;this->ids=ids;
    }
    synchronized Order place(std::string userId, std::string address, std::string instructions){
        Cart cart = carts.byUser(userId).orElseThrow(()->new DomainException("empty cart"));
        if (cart.items.isEmpty()) throw new DomainException("empty cart");
        Restaurant rest = restaurants.byId(cart.restaurantId).orElseThrow(()->new DomainException("restaurant"));
        // snapshot items
        std::vector<OrderItem> items = std::vector<>{};
        for (CartItem ci: cart.items.values()){
            MenuItem mi = menu.byId(ci.itemId).orElseThrow(()->new DomainException("menu item missing"));
            if (!mi.inStock) throw new DomainException("item went out of stock: "+mi.name);
            items.add(new OrderItem(mi.id, mi.name, mi.price, ci.qty));
        }
        double sub = pricing.subTotal(items);
        // distance approx: pretend user's address is 2km away baseline (for demo).
        double distKm = 2.0; // could be from geocode(address)
        double delivery = pricing.deliveryFee(distKm);
        double tax = pricing.tax(sub);
        double total = pricing.total(sub, tax, delivery);
        Order order = new Order(ids.next("ord"), userId, rest.id, address, instructions, items, sub, tax, delivery, total);
        carts.delete(userId); // clear cart
        return orders.save(order);
    }
    void setStatus(std::string orderId, OrderStatus st){
        Order o = orders.byId(orderId).orElseThrow(()->new DomainException("order"));
        o.status = st; orders.save(o);
    }
}
class PaymentService {
    const PaymentRepo payments; const OrderRepo orders; const Ids ids;
    PaymentService(PaymentRepo p, OrderRepo o, Ids ids){payments=p;orders=o;this->ids=ids;}
    synchronized Payment confirm(std::string orderId, std::string method, std::string txnRef){
        Order o = orders.byId(orderId).orElseThrow(()->new DomainException("order"));
        Payment pay = new Payment(ids.next("pay"), orderId, method, txnRef, o.total);
        pay.status = PaymentStatus.PAID; pay.paidAt = Instant.now();
        orders.save(o); // status handled externally
        return payments.save(pay);
    }
}
class AssignmentService {
    const PartnerRepo partners; const RestaurantRepo restaurants; const OrderRepo orders;
    AssignmentService(PartnerRepo p, RestaurantRepo r, OrderRepo o){partners=p;restaurants=r;orders=o;}
    synchronized DeliveryPartner assign(std::string orderId){
        Order o = orders.byId(orderId).orElseThrow(()->new DomainException("order"));
        Restaurant r = restaurants.byId(o.restaurantId).orElseThrow(()->new DomainException("restaurant"));
        std::vector<DeliveryPartner> avail = partners.available();
        if (avail.isEmpty()) throw new DomainException("no partner available");
        // nearest partner by distance to restaurant
        DeliveryPartner best = avail.stream()
                .min(Comparator.comparingDouble(p->Haversine.distanceKm(p.loc, r.loc))).get();
        best.available = false;
        double km = Haversine.distanceKm(best.loc, r.loc);
        int eta = Haversine.etaMin(km + 2.0); // add 2km headroom to destination
        o.partnerId = best.id; o.etaMin = eta; orders.save(o);
        return best;
    }
    synchronized void markDelivered(std::string orderId){
        Order o = orders.byId(orderId).orElseThrow(()->new DomainException("order"));
        if (o.partnerId!=nullptr){
            partners.byId(o.partnerId).ifPresent(p->p.available=true);
        }
        o.status = OrderStatus.DELIVERED; orders.save(o);
    }
}
class TrackingService {
    const OrderRepo orders; const PartnerRepo partners; const RestaurantRepo restaurants;
    TrackingService(OrderRepo o, PartnerRepo p, RestaurantRepo r){orders=o;partners=p;restaurants=r;}
    std::unordered_map<std::string,auto> track(std::string orderId){
        Order o = orders.byId(orderId).orElseThrow(()->new DomainException("order"));
        std::unordered_map<std::string,auto> m = std::unordered_map<>{};
        m.put("status", o.status.name());
        m.put("etaMin", o.etaMin);
        if (o.partnerId!=nullptr) {
            partners.byId(o.partnerId).ifPresent(dp->{
                m.put("partnerId", dp.id);
                m.put("partnerLoc", Map.of("lat", dp.loc.lat, "lon", dp.loc.lon));
            });
        }
        return m;
    }
}

/* ===== Controller Facade ===== */
class FoodController {
    const CatalogService catalog; const CartService carts; const OrderService orders;
    const PaymentService payments; const AssignmentService assign; const TrackingService tracking;

    FoodController(CatalogService c, CartService ca, OrderService o, PaymentService p, AssignmentService a, TrackingService t){
        catalog=c; carts=ca; orders=o; payments=p; assign=a; tracking=t;
    }

    std::vector<Restaurant> getRestaurants(std::string area,std::string cuisine){ return catalog.search(area, cuisine); }
    std::vector<MenuItem> getMenu(std::string restaurantId){ return catalog.menu(restaurantId); }

    Cart postCartAdd(std::string userId, std::string restaurantId, std::string itemId, int qty){ return carts.addItem(userId, restaurantId, itemId, qty); }
    Cart deleteCartItem(std::string userId, std::string itemId){ return carts.removeItem(userId, itemId); }

    Order postOrder(std::string userId, std::string address, std::string instructions){ return orders.place(userId, address, instructions); }
    Payment postPaymentConfirm(std::string orderId, std::string method, std::string txnRef){ return payments.confirm(orderId, method, txnRef); }

    DeliveryPartner postAssign(std::string orderId){
        DeliveryPartner dp = assign.assign(orderId);
        orders.setStatus(orderId, OrderStatus.PREPARING);
        return dp;
    }
    std::unordered_map<std::string,auto> getTrack(std::string orderId){ return tracking.track(orderId); }
}

/* ===== Bootstrap & Minimal Demo ===== */
class SwiggyZomato40Min {
    int main() {
        Ids ids = new Ids();
        // Repos
        RestaurantRepo restaurants = new RestaurantRepo();
        MenuRepo menu = new MenuRepo();
        CartRepo carts = new CartRepo();
        OrderRepo orders = new OrderRepo();
        PaymentRepo pays = new PaymentRepo();
        PartnerRepo partners = new PartnerRepo();

        // Seed Restaurants & Menu
        Restaurant r1 = restaurants.save(new Restaurant(ids.next("rest"), "Punjabi Zaika", "HSR", List.of("NorthIndian","Biryani"), new GeoPoint(12.91,77.64), 4.4));
        Restaurant r2 = restaurants.save(new Restaurant(ids.next("rest"), "Veggie Delite", "HSR", List.of("SouthIndian","Healthy"), new GeoPoint(12.905,77.64), 4.6));

        menu.save(new MenuItem(ids.next("item"), r1.id, "Butter Chicken", 280, false, true));
        menu.save(new MenuItem(ids.next("item"), r1.id, "Dal Makhani", 180, true, true));
        menu.save(new MenuItem(ids.next("item"), r2.id, "Veg Thali", 220, true, true));

        // Partners
        partners.save(new DeliveryPartner(ids.next("dp"), "Ravi", new GeoPoint(12.90,77.62), true, 4.8));
        partners.save(new DeliveryPartner(ids.next("dp"), "Kiran", new GeoPoint(12.92,77.65), true, 4.5));

        // Services
        CatalogService catalog = new CatalogService(restaurants, menu);
        PricingService pricing = new PricingService();
        CartService cartSvc = new CartService(carts, menu, ids);
        OrderService orderSvc = new OrderService(orders, carts, menu, pricing, restaurants, ids);
        PaymentService paymentSvc = new PaymentService(pays, orders, ids);
        AssignmentService assign = new AssignmentService(partners, restaurants, orders);
        TrackingService tracking = new TrackingService(orders, partners, restaurants);

        // Controller
        FoodController api = new FoodController(catalog, cartSvc, orderSvc, paymentSvc, assign, tracking);

        // --- Demo like API calls ---
        std::cout << "GET /restaurants?area=HSR&cuisine=NorthIndian\n" + api.getRestaurants("HSR","NorthIndian")) << std::endl;
        std::cout << "\nGET /restaurants/{id}/menu\n" + api.getMenu(r1.id)) << std::endl;

        std::string user = "user-007";
        var c1 = api.postCartAdd(user, r1.id, api.getMenu(r1.id).get(0).id, 1);
        var c2 = api.postCartAdd(user, r1.id, api.getMenu(r1.id).get(1).id, 2);
        std::cout << "\nPOST /cart/items -> cart items: " + c2.items.values().stream().map(ci->ci.itemId+":"+ci.qty).collect(Collectors.toList())) << std::endl;

        Order ord = api.postOrder(user, "HSR Layout, Bengaluru", "Less spicy");
        std::cout << "\nPOST /orders -> " + ord.id + " total=" + ord.total) << std::endl;

        var pay = api.postPaymentConfirm(ord.id, "UPI", "TXN-42");
        orders.byId(ord.id).ifPresent(o->o.status=OrderStatus.PAID);
        std::cout << "POST /payments/confirm -> " + pay.status + " amount=" + pay.amount) << std::endl;

        DeliveryPartner dp = api.postAssign(ord.id);
        std::cout << "\nPOST /orders/{id}/assign -> partner=" + dp.name + " etaMin=" + orders.byId(ord.id).get().etaMin) << std::endl;

        orders.byId(ord.id).ifPresent(o->o.status=OrderStatus.PICKED_UP);
        std::cout << "\nGET /orders/{id}/track -> " + api.getTrack(ord.id)) << std::endl;

        assign.markDelivered(ord.id);
        std::cout << "\nDelivered. Track -> " + api.getTrack(ord.id)) << std::endl;
    }
}
```

## Ride Sharing

```
/*
Template ->
1) define functional requirements
   - Rider requests a ride (pickup, drop, carType).
   - System matches nearest available driver; returns ETA & fare estimate.
   - Rider can confirm -> ride gets ACCEPTED; driver can start and end trip.
   - Pricing = base + perKm + perMin with simple surge (demand/supply).
   - Track ride: live status, driver location, ETA.
   - Payment confirmation (stub) after completion.
   - In-memory, single city, thread-safe where needed — doable in ~40 min.

2) define entities / actors
   Actors: Rider, Driver
   Entities: Rider, Driver(availability, loc), Ride(status lifecycle), Payment

3) define apis - get/post/put, request, response
   POST /riders                       {name} -> {riderId}
   POST /drivers                      {name, carType, lat, lon} -> {driverId}
   PUT  /drivers/{id}/location        {lat, lon, available} -> {ok}
   POST /rides/quote                  {riderId, pickup{lat,lon}, drop{lat,lon}, carType} -> {quoteId, driverId, etaMin, fareEstimate}
   POST /rides/confirm                {quoteId} -> {rideId, status}
   POST /rides/{rideId}/start         {} -> {status}
   POST /rides/{rideId}/end           {} -> {fare, status}
   POST /payments                     {rideId, method, txnRef?} -> {paymentId, status}
   GET  /rides/{rideId}/track         -> {status, driverLoc, etaMin}

4) define services involved
   MatchingService     - nearest available driver by carType.
   PricingService      - distance, time estimate, fare + surge.
   RideService         - create/confirm/start/end rides, state machine.
   DriverService       - update location/availability.
   PaymentService      - confirm payments (stub).
   TrackingService     - ETA/status view.
   IdGenerator         - generate IDs.

5) define db schema - what all tables are required, what are the columns, what are the keys
   rider(id PK, name, created_at)
   driver(id PK, name, car_type, lat, lon, available BOOL, rating)
   ride(id PK, rider_id FK, driver_id FK, pickup_lat, pickup_lon, drop_lat, drop_lon, car_type, 
        requested_at, accepted_at, started_at, ended_at, distance_km, duration_min, fare, status)
   payment(id PK, ride_id FK UNIQUE, method, amount, status, txn_ref, paid_at)
*/
```

### C++ Implementation

```cpp
#include <bits/stdc++.h>
using namespace std;
/*
Template ->
1) define functional requirements
   - Rider requests a ride (pickup, drop, carType).
   - System matches nearest available driver; returns ETA & fare estimate.
   - Rider can confirm -> ride gets ACCEPTED; driver can start and end trip.
   - Pricing = base + perKm + perMin with simple surge (demand/supply).
   - Track ride: live status, driver location, ETA.
   - Payment confirmation (stub) after completion.
   - In-memory, single city, thread-safe where needed — doable in ~40 min.

2) define entities / actors
   Actors: Rider, Driver
   Entities: Rider, Driver(availability, loc), Ride(status lifecycle), Payment

3) define apis - get/post/put, request, response
   POST /riders                       {name} -> {riderId}
   POST /drivers                      {name, carType, lat, lon} -> {driverId}
   PUT  /drivers/{id}/location        {lat, lon, available} -> {ok}
   POST /rides/quote                  {riderId, pickup{lat,lon}, drop{lat,lon}, carType} -> {quoteId, driverId, etaMin, fareEstimate}
   POST /rides/confirm                {quoteId} -> {rideId, status}
   POST /rides/{rideId}/start         {} -> {status}
   POST /rides/{rideId}/end           {} -> {fare, status}
   POST /payments                     {rideId, method, txnRef?} -> {paymentId, status}
   GET  /rides/{rideId}/track         -> {status, driverLoc, etaMin}

4) define services involved
   MatchingService     - nearest available driver by carType.
   PricingService      - distance, time estimate, fare + surge.
   RideService         - create/confirm/start/end rides, state machine.
   DriverService       - update location/availability.
   PaymentService      - confirm payments (stub).
   TrackingService     - ETA/status view.
   IdGenerator         - generate IDs.

5) define db schema - what all tables are required, what are the columns, what are the keys
   rider(id PK, name, created_at)
   driver(id PK, name, car_type, lat, lon, available BOOL, rating)
   ride(id PK, rider_id FK, driver_id FK, pickup_lat, pickup_lon, drop_lat, drop_lon, car_type, 
        requested_at, accepted_at, started_at, ended_at, distance_km, duration_min, fare, status)
   payment(id PK, ride_id FK UNIQUE, method, amount, status, txn_ref, paid_at)
*/
/* ===== Domain ===== */
enum CarType { MINI, SEDAN, SUV }
enum RideStatus { QUOTED, ACCEPTED, ONGOING, COMPLETED, CANCELLED }
enum PaymentStatus { PENDING, PAID, FAILED }

const class Geo { const double lat, lon; Geo(double lat,double lon){this->lat=lat;this->lon=lon;} }

const class Rider { const std::string id, name; const Instant createdAt=Instant.now(); Rider(std::string id,std::string n){this->id=id;this->name=n;} }
const class Driver {
    const std::string id, name; const CarType carType; volatile Geo loc; volatile boolean available=true; const double rating;
    Driver(std::string id,std::string n,CarType c,Geo l,double r){this->id=id;this->name=n;this->carType=c;this->loc=l;this->rating=r;}
}

const class Ride {
    const std::string id, riderId; std::string driverId;
    const CarType carType; const Geo pickup, drop;
    const Instant requestedAt=Instant.now();
    volatile Instant acceptedAt, startedAt, endedAt;
    volatile double distanceKm, durationMin, fare;
    volatile RideStatus status = RideStatus.QUOTED; // after quote; becomes ACCEPTED on confirm
    Ride(std::string id,std::string riderId,CarType carType,Geo pickup,Geo drop){
        this->id=id; this->riderId=riderId; this->carType=carType; this->pickup=pickup; this->drop=drop;
    }
}

const class Payment {
    const std::string id, rideId, method, txnRef; const double amount;
    volatile PaymentStatus status=PaymentStatus.PENDING; volatile Instant paidAt;
    Payment(std::string id,std::string rideId,std::string method,std::string txnRef,double amount){
        this->id=id; this->rideId=rideId; this->method=method; this->txnRef=txnRef; this->amount=amount;
    }
}

/* ===== Utils ===== */
class Ids { const AtomicLong n=new AtomicLong(1); std::string next(std::string p){return p+"-"+n.getAndIncrement();} }
class Haversine {
    static double km(Geo a, Geo b){
        double R=6371, dLat=Math.toRadians(b.lat-a.lat), dLon=Math.toRadians(b.lon-a.lon);
        double s1=Math.sin(dLat/2), s2=Math.sin(dLon/2);
        double h=s1*s1 + Math.cos(Math.toRadians(a.lat))*Math.cos(Math.toRadians(b.lat))*s2*s2;
        return 2*R*Math.asin(Math.sqrt(h));
    }
}

/* ===== Repos (in-memory) ===== */
class RiderRepo { const std::unordered_map<std::string,Rider> m=new ConcurrentHashMap<>(); Rider save(Rider x){m.put(x.id,x);return x;} std::optional<Rider> byId(std::string id){return Optional.ofNullable(m.get(id));} }
class DriverRepo {
    const std::unordered_map<std::string,Driver> m=new ConcurrentHashMap<>();
    Driver save(Driver d){m.put(d.id,d);return d;}
    std::optional<Driver> byId(std::string id){return Optional.ofNullable(m.get(id));}
    std::vector<Driver> availableByType(CarType t){ return m.values().stream().filter(d->d.available && d.carType==t).collect(Collectors.toList()); }
}
class RideRepo {
    const std::unordered_map<std::string,Ride> m=new ConcurrentHashMap<>();
    Ride save(Ride r){m.put(r.id,r);return r;}
    std::optional<Ride> byId(std::string id){return Optional.ofNullable(m.get(id));}
}
class PaymentRepo { const std::unordered_map<std::string,Payment> m=new ConcurrentHashMap<>(); Payment save(Payment p){m.put(p.id,p);return p;} std::optional<Payment> byRide(std::string rideId){return m.values().stream().filter(x->x.rideId == (rideId)).findFirst();} }

/* ===== Services ===== */
class DriverService {
    const DriverRepo drivers;
    DriverService(DriverRepo d){drivers=d;}
    Driver register(std::string name, CarType type, double lat, double lon){
        Driver d = new Driver(Uber40Min.ids.next("drv"), name, type, new Geo(lat,lon), 4.7);
        return drivers.save(d);
    }
    void updateLocation(std::string driverId, double lat, double lon, boolean available){
        Driver d = drivers.byId(driverId).orElseThrow(()->new RuntimeException("driver"));
        d.loc = new Geo(lat,lon); d.available = available; drivers.save(d);
    }
}

class PricingService {
    // base fare per car type
    static const std::unordered_map<CarType,double> BASE = Map.of(CarType.MINI,30.0, CarType.SEDAN,40.0, CarType.SUV,55.0);
    static const std::unordered_map<CarType,double> PER_KM = Map.of(CarType.MINI,12.0, CarType.SEDAN,14.0, CarType.SUV,18.0);
    static const std::unordered_map<CarType,double> PER_MIN= Map.of(CarType.MINI,1.5 , CarType.SEDAN,2.0 , CarType.SUV,2.5 );

    double surgeFactor(int demand, int supply){
        if (supply<=0) return 2.0;
        double ratio = (double)demand / supply; // >1 means surge
        return Math.min(2.5, Math.max(1.0, 1.0 + (ratio-1.0)*0.8)); // soft clamp
    }

    double estimateFare(CarType type, double km, double minutes, double surge){
        double fare = BASE.get(type) + PER_KM.get(type)*km + PER_MIN.get(type)*minutes;
        return round2(fare * surge);
    }
    static double round2(double v){ return Math.round(v*100.0)/100.0; }
}

class MatchingService {
    const DriverRepo drivers;
    MatchingService(DriverRepo d){drivers=d;}
    std::optional<Driver> nearest(CarType type, Geo pickup){
        return drivers.availableByType(type).stream()
                .min(Comparator.comparingDouble(d->Haversine.km(d.loc, pickup)));
    }
}

const class Quote {
    const std::string id, riderId; const CarType carType; const Geo pickup, drop;
    const std::string driverId; const int etaMin; const double fareEstimate;
    Quote(std::string id,std::string riderId,CarType carType,Geo p,Geo d,std::string driverId,int etaMin,double fare){
        this->id=id; this->riderId=riderId; this->carType=carType; this->pickup=p; this->drop=d; this->driverId=driverId; this->etaMin=etaMin; this->fareEstimate=fare;
    }
}

class RideService {
    const RideRepo rides; const DriverRepo drivers; const MatchingService match; const PricingService pricing;
    const std::unordered_map<std::string,Quote> quotes = new ConcurrentHashMap<>();

    RideService(RideRepo r, DriverRepo d, MatchingService m, PricingService p){rides=r;drivers=d;match=m;pricing=p;}

    Quote quote(std::string riderId, CarType type, Geo pickup, Geo drop){
        // naive ETA: distance from driver to pickup at 22km/h
        std::optional<Driver> cand = match.nearest(type, pickup);
        if (cand.isEmpty()) throw new RuntimeException("no driver available");
        Driver drv = cand.get();
        double distToPickupKm = Haversine.km(drv.loc, pickup);
        int etaMin = Math.max(2, (int)Math.round(distToPickupKm / 0.37)); // ~22 km/h

        // trip distance & duration estimate
        double tripKm = Haversine.km(pickup, drop) * 1.2; // 20% road factor
        double minutes = Math.max(10, tripKm / 0.35);     // ~21 km/h avg

        // surge factor from simple demand/supply around car type
        int demand=1; int supply = drivers.availableByType(type).size();
        double surge = pricing.surgeFactor(demand, supply);
        double estimate = pricing.estimateFare(type, tripKm, minutes, surge);

        std::string qid = Uber40Min.ids.next("quote");
        Quote q = new Quote(qid, riderId, type, pickup, drop, drv.id, etaMin, estimate);
        quotes.put(qid, q);
        return q;
    }

    synchronized Ride confirm(std::string quoteId){
        Quote q = Optional.ofNullable(quotes.remove(quoteId)).orElseThrow(()->new RuntimeException("quote expired"));
        Driver d = drivers.byId(q.driverId).orElseThrow(()->new RuntimeException("driver missing"));
        if (!d.available) throw new RuntimeException("driver just got busy");
        d.available = false; drivers.save(d);

        Ride ride = new Ride(Uber40Min.ids.next("ride"), q.riderId, q.carType, q.pickup, q.drop);
        ride.driverId = q.driverId;
        ride.acceptedAt = Instant.now();
        ride.status = RideStatus.ACCEPTED;
        return rides.save(ride);
    }

    synchronized Ride start(std::string rideId){
        Ride r = rides.byId(rideId).orElseThrow(()->new RuntimeException("ride"));
        if (r.status != RideStatus.ACCEPTED) throw new RuntimeException("not ready to start");
        r.startedAt = Instant.now(); r.status = RideStatus.ONGOING;
        return rides.save(r);
    }

    synchronized Ride end(std::string rideId){
        Ride r = rides.byId(rideId).orElseThrow(()->new RuntimeException("ride"));
        if (r.status != RideStatus.ONGOING) throw new RuntimeException("not ongoing");
        r.endedAt = Instant.now();
        // compute actuals (in demo use straight estimates)
        double tripKm = Haversine.km(r.pickup, r.drop) * 1.2;
        double minutes = Math.max(10, Duration.between(r.startedAt, r.endedAt).toMinutes());
        double surge = 1.0;
        r.distanceKm = round2(tripKm); r.durationMin = round2(minutes);
        r.fare = PricingService.round2(new PricingService().estimateFare(r.carType, tripKm, minutes, surge));
        r.status = RideStatus.COMPLETED;
        rides.save(r);

        // free driver
        Driver d = drivers.byId(r.driverId).orElseThrow();
        d.available = true; drivers.save(d);
        return r;
    }

    static double round2(double v){ return Math.round(v*100.0)/100.0; }
}

class PaymentService {
    const PaymentRepo payments; PaymentService(PaymentRepo p){payments=p;}
    Payment confirm(std::string rideId, double amount, std::string method, std::string txnRef){
        Payment pay = new Payment(Uber40Min.ids.next("pay"), rideId, method, txnRef, amount);
        pay.status = PaymentStatus.PAID; pay.paidAt = Instant.now();
        return payments.save(pay);
    }
}

class TrackingService {
    const RideRepo rides; const DriverRepo drivers;
    TrackingService(RideRepo r, DriverRepo d){rides=r;drivers=d;}
    std::unordered_map<std::string,auto> track(std::string rideId){
        Ride ride = rides.byId(rideId).orElseThrow(()->new RuntimeException("ride"));
        std::unordered_map<std::string,auto> m = std::unordered_map<>{};
        m.put("status", ride.status.name());
        if (ride.driverId!=nullptr){
            Driver d = drivers.byId(ride.driverId).orElse(nullptr);
            if (d!=nullptr) {
                m.put("driverId", d.id);
                m.put("driverLoc", Map.of("lat", d.loc.lat, "lon", d.loc.lon));
                int eta = ride.status==RideStatus.ACCEPTED ? Math.max(2,(int)Math.round(Haversine.km(d.loc, ride.pickup)/0.37)) :
                          ride.status==RideStatus.ONGOING  ? Math.max(2,(int)Math.round(Haversine.km(d.loc, ride.drop)/0.37)) : 0;
                m.put("etaMin", eta);
            }
        }
        return m;
    }
}

/* ===== Controller Facade (mirrors APIs) ===== */
class UberController {
    const DriverService driverSvc; const RideService rideSvc; const PricingService pricing;
    const PaymentService paySvc; const TrackingService tracking;

    UberController(DriverService d, RideService r, PricingService p, PaymentService pay, TrackingService t){
        driverSvc=d; rideSvc=r; pricing=p; paySvc=pay; tracking=t;
    }

    Rider postRider(RiderRepo riders, std::string name){ Rider r = new Rider(Uber40Min.ids.next("r"), name); return riders.save(r); }
    Driver postDriver(std::string name, CarType type, double lat, double lon){ return driverSvc.register(name, type, lat, lon); }
    void putDriverLocation(std::string driverId, double lat, double lon, boolean available){ driverSvc.updateLocation(driverId, lat, lon, available); }

    Quote postQuote(std::string riderId, CarType type, Geo pickup, Geo drop){ return rideSvc.quote(riderId, type, pickup, drop); }
    Ride postConfirm(std::string quoteId){ return rideSvc.confirm(quoteId); }
    Ride postStart(std::string rideId){ return rideSvc.start(rideId); }
    Ride postEnd(std::string rideId){ return rideSvc.end(rideId); }
    Payment postPayment(std::string rideId, double amount, std::string method, std::string txnRef){ return paySvc.confirm(rideId, amount, method, txnRef); }
    std::unordered_map<std::string,auto> getTrack(std::string rideId){ return tracking.track(rideId); }
}

/* ===== Demo (tiny, 40-min friendly) ===== */
class Uber40Min {
    static const Ids ids = new Ids();

    int main() {
        // Repos
        RiderRepo riders = new RiderRepo();
        DriverRepo drivers = new DriverRepo();
        RideRepo rideRepo = new RideRepo();
        PaymentRepo payRepo = new PaymentRepo();

        // Services
        DriverService driverSvc = new DriverService(drivers);
        PricingService pricing = new PricingService();
        MatchingService matcher = new MatchingService(drivers);
        RideService rideSvc = new RideService(rideRepo, drivers, matcher, pricing);
        PaymentService paySvc = new PaymentService(payRepo);
        TrackingService tracking = new TrackingService(rideRepo, drivers);

        UberController api = new UberController(driverSvc, rideSvc, pricing, paySvc, tracking);

        // Seed riders & drivers
        Rider r1 = api.postRider(riders, "Aarav");
        Driver d1 = api.postDriver("Ravi", CarType.SEDAN, 12.912, 77.641);
        Driver d2 = api.postDriver("Kiran", CarType.SEDAN, 12.915, 77.63);
        Driver d3 = api.postDriver("Rohit", CarType.MINI , 12.90 , 77.62);

        // Rider requests a quote (SEDAN)
        Geo pickup = new Geo(12.914, 77.638);
        Geo drop   = new Geo(12.935, 77.624);
        Quote q = api.postQuote(r1.id, CarType.SEDAN, pickup, drop);
        std::cout << "QUOTE -> driver="+q.driverId+" etaMin="+q.etaMin+" fareEst="+q.fareEstimate) << std::endl;

        // Rider confirms
        Ride ride = api.postConfirm(q.id);
        std::cout << "CONFIRM -> rideId="+ride.id+" status="+ride.status) << std::endl;

        std::cout << "TRACK pre-start -> "+api.getTrack(ride.id)) << std::endl;
        api.postStart(ride.id);
        std::cout << "START -> status="+rideRepo.byId(ride.id).get().status) << std::endl;

        // Simulate driving...
        Thread.sleep(1000);
        api.putDriverLocation(ride.driverId, 12.925, 77.63, false);
        std::cout << "TRACK mid -> "+api.getTrack(ride.id)) << std::endl;

        // End ride
        Ride ended = api.postEnd(ride.id);
        std::cout << "END -> fare="+ended.fare+" status="+ended.status) << std::endl;

        // Payment
        Payment pay = api.postPayment(ride.id, ended.fare, "UPI", "TXN-7788");
        std::cout << "PAYMENT -> "+pay.status+" amount="+pay.amount) << std::endl;
    }
}
```

## Chat App

```
/*
Template ->
1) define functional requirements
   - One-to-one and group chats.
   - Send/receive text messages; mark as delivered/read.
   - Fetch chat history with pagination (cursor/limit).
   - Maintain online/offline status.
   - Simple in-memory pub-sub style notifications (stub).
   - Lightweight, concurrency-safe where needed; doable in ~40 min.

2) define entities / actors
   Actors: User
   Entities: User, Chat (1-1 or group), Message, Participant, Presence

3) define apis - get/post/put, request, response
   POST   /users                        {name} -> {userId}
   POST   /chats                        {creatorId, participantIds:[...], groupName?} -> {chatId}
   POST   /chats/{chatId}/messages      {senderId, text} -> {messageId, ts}
   GET    /chats/{chatId}/messages      {cursor?, limit} -> [{messageId, senderId, text, ts, status}]
   PUT    /messages/{id}/delivered      {userId} -> {ok}
   PUT    /messages/{id}/read           {userId} -> {ok}
   PUT    /users/{id}/presence          {online} -> {ok}

4) define services involved
   UserService       - create users, update presence.
   ChatService       - create chat, add participants.
   MessageService    - send messages, mark delivered/read.
   HistoryService    - fetch chat history with pagination.
   NotificationService- stub for notifying participants.
   IdGenerator       - generate IDs.

5) define db schema - what all tables are required, what are the columns, what are the keys
   user(id PK, name, online BOOL, created_at)
   chat(id PK, group_name NULL, is_group BOOL, created_at)
   chat_participant(chat_id FK, user_id FK, joined_at)
   message(id PK, chat_id FK, sender_id FK, text, created_at, status ENUM)
   message_status(message_id FK, user_id FK, delivered_at, read_at)
*/
```

### C++ Implementation

```cpp
#include <bits/stdc++.h>
using namespace std;
/*
Template ->
1) define functional requirements
   - One-to-one and group chats.
   - Send/receive text messages; mark as delivered/read.
   - Fetch chat history with pagination (cursor/limit).
   - Maintain online/offline status.
   - Simple in-memory pub-sub style notifications (stub).
   - Lightweight, concurrency-safe where needed; doable in ~40 min.

2) define entities / actors
   Actors: User
   Entities: User, Chat (1-1 or group), Message, Participant, Presence

3) define apis - get/post/put, request, response
   POST   /users                        {name} -> {userId}
   POST   /chats                        {creatorId, participantIds:[...], groupName?} -> {chatId}
   POST   /chats/{chatId}/messages      {senderId, text} -> {messageId, ts}
   GET    /chats/{chatId}/messages      {cursor?, limit} -> [{messageId, senderId, text, ts, status}]
   PUT    /messages/{id}/delivered      {userId} -> {ok}
   PUT    /messages/{id}/read           {userId} -> {ok}
   PUT    /users/{id}/presence          {online} -> {ok}

4) define services involved
   UserService       - create users, update presence.
   ChatService       - create chat, add participants.
   MessageService    - send messages, mark delivered/read.
   HistoryService    - fetch chat history with pagination.
   NotificationService- stub for notifying participants.
   IdGenerator       - generate IDs.

5) define db schema - what all tables are required, what are the columns, what are the keys
   user(id PK, name, online BOOL, created_at)
   chat(id PK, group_name NULL, is_group BOOL, created_at)
   chat_participant(chat_id FK, user_id FK, joined_at)
   message(id PK, chat_id FK, sender_id FK, text, created_at, status ENUM)
   message_status(message_id FK, user_id FK, delivered_at, read_at)
*/
/* ===== Domain ===== */
enum MessageStatus { SENT, DELIVERED, READ }

const class User { const std::string id,name; volatile boolean online=false; const Instant createdAt=Instant.now(); User(std::string id,std::string n){this->id=id;this->name=n;} }
const class Chat { const std::string id, groupName; const boolean isGroup; const std::unordered_set<std::string> participants=std::unordered_set<>{}; const Instant createdAt=Instant.now();
    Chat(std::string id,boolean isGroup,std::string groupName){this->id=id;this->isGroup=isGroup;this->groupName=groupName;}
}
const class Message {
    const std::string id, chatId, senderId, text; const Instant createdAt=Instant.now();
    const std::unordered_map<std::string,MessageStatus> perUser=new ConcurrentHashMap<>(); // userId -> status
    Message(std::string id,std::string chatId,std::string senderId,std::string text){this->id=id;this->chatId=chatId;this->senderId=senderId;this->text=text;}
}

/* ===== Utils ===== */
class Ids { const AtomicLong n=new AtomicLong(1); std::string next(std::string p){return p+"-"+n.getAndIncrement();} }

/* ===== Repos ===== */
class UserRepo { const std::unordered_map<std::string,User> m=new ConcurrentHashMap<>(); User save(User u){m.put(u.id,u);return u;} std::optional<User> byId(std::string id){return Optional.ofNullable(m.get(id));} }
class ChatRepo { const std::unordered_map<std::string,Chat> m=new ConcurrentHashMap<>(); Chat save(Chat c){m.put(c.id,c);return c;} std::optional<Chat> byId(std::string id){return Optional.ofNullable(m.get(id));} }
class MsgRepo { const std::unordered_map<std::string,Message> m=new ConcurrentHashMap<>(); Message save(Message x){m.put(x.id,x);return x;} std::optional<Message> byId(std::string id){return Optional.ofNullable(m.get(id));} std::vector<Message> byChat(std::string chatId){return m.values().stream().filter(m->m.chatId == (chatId)).sorted(Comparator.comparing((Message x)->x.createdAt)).collect(Collectors.toList());} }

/* ===== Services ===== */
class UserService {
    const UserRepo users; const Ids ids;
    UserService(UserRepo u,Ids ids){users=u;this->ids=ids;}
    User create(std::string name){ return users.save(new User(ids.next("u"),name)); }
    void setPresence(std::string id, boolean online){ users.byId(id).ifPresent(u->u.online=online); }
}

class ChatService {
    const ChatRepo chats; const UserRepo users; const Ids ids;
    ChatService(ChatRepo c,UserRepo u,Ids ids){chats=c;users=u;this->ids=ids;}
    Chat create(std::string creatorId, std::unordered_set<std::string> parts, boolean isGroup, std::string groupName){
        Chat c = new Chat(ids.next("chat"),isGroup,groupName);
        c.participants.add(creatorId); c.participants.addAll(parts);
        return chats.save(c);
    }
}

class MessageService {
    const MsgRepo msgs; const ChatRepo chats; const Ids ids;
    MessageService(MsgRepo m,ChatRepo c,Ids ids){msgs=m;chats=c;this->ids=ids;}
    Message send(std::string chatId,std::string senderId,std::string text){
        Chat c=chats.byId(chatId).orElseThrow(()->new RuntimeException("chat not found"));
        if(!c.participants.contains(senderId)) throw new RuntimeException("not in chat");
        Message m=new Message(ids.next("msg"),chatId,senderId,text);
        for(std::string uid:c.participants){ m.perUser.put(uid, uid == (senderId)?MessageStatus.READ:MessageStatus.SENT); }
        return msgs.save(m);
    }
    void delivered(std::string msgId,std::string userId){ Message m=msgs.byId(msgId).orElseThrow(); m.perUser.put(userId,MessageStatus.DELIVERED); }
    void read(std::string msgId,std::string userId){ Message m=msgs.byId(msgId).orElseThrow(); m.perUser.put(userId,MessageStatus.READ); }
}

class HistoryService {
    const MsgRepo msgs;
    HistoryService(MsgRepo m){msgs=m;}
    std::vector<Message> getHistory(std::string chatId, std::string cursor, int limit){
        std::vector<Message> all=msgs.byChat(chatId);
        int start=0;
        if(cursor!=nullptr){
            for(int i=0;i<all.size();i++){ if(all.get(i).id == (cursor)){ start=i+1; break; } }
        }
        return all.stream().skip(start).limit(limit).collect(Collectors.toList());
    }
}

/* ===== Controller ===== */
class ChatController {
    const UserService users; const ChatService chats; const MessageService msgs; const HistoryService history;
    ChatController(UserService u,ChatService c,MessageService m,HistoryService h){users=u;chats=c;msgs=m;history=h;}

    User postUser(std::string name){ return users.create(name); }
    void putPresence(std::string id, boolean online){ users.setPresence(id,online); }

    Chat postChat(std::string creatorId, std::unordered_set<std::string> parts, boolean isGroup, std::string groupName){ return chats.create(creatorId,parts,isGroup,groupName); }

    Message postMessage(std::string chatId,std::string senderId,std::string text){ return msgs.send(chatId,senderId,text); }
    void putDelivered(std::string msgId,std::string userId){ msgs.delivered(msgId,userId); }
    void putRead(std::string msgId,std::string userId){ msgs.read(msgId,userId); }

    std::vector<Message> getHistory(std::string chatId,std::string cursor,int limit){ return history.getHistory(chatId,cursor,limit); }
}

/* ===== Demo ===== */
class WhatsApp40Min {
    int main() {
        Ids ids=new Ids(); UserRepo userRepo=new UserRepo(); ChatRepo chatRepo=new ChatRepo(); MsgRepo msgRepo=new MsgRepo();
        UserService userSvc=new UserService(userRepo,ids);
        ChatService chatSvc=new ChatService(chatRepo,userRepo,ids);
        MessageService msgSvc=new MessageService(msgRepo,chatRepo,ids);
        HistoryService histSvc=new HistoryService(msgRepo);
        ChatController api=new ChatController(userSvc,chatSvc,msgSvc,histSvc);

        User a=api.postUser("Alice"), b=api.postUser("Bob");
        api.putPresence(a.id,true); api.putPresence(b.id,true);

        Chat chat=api.postChat(a.id,Set.of(b.id),false,nullptr);
        std::cout << "Chat created: "+chat.id) << std::endl;

        Message m1=api.postMessage(chat.id,a.id,"Hi Bob!");
        Message m2=api.postMessage(chat.id,b.id,"Hey Alice!");
        api.putDelivered(m1.id,b.id); api.putRead(m1.id,b.id);

        std::cout << "History: ") << std::endl;
        for(Message m: api.getHistory(chat.id,nullptr,10)){
            std::cout << m.id+" from "+m.senderId+": "+m.text+" statuses="+m.perUser) << std::endl;
        }
    }
}
```

## File Store

```
/*
Template ->
1) define functional requirements
   - Create folders/files; hierarchical tree with root per user.
   - Upload file (new file or new version), download (stub returns bytes length), rename, move, delete (trash) & restore.
   - Share file/folder with users with permissions: VIEW, EDIT, OWNER (owner implicit).
   - List folder contents with pagination (cursor+limit).
   - Search by name (prefix/substring) within items user can access.
   - Version history: list versions, restore a previous version.
   - In-memory only; 40-min interview friendly; single JVM; basic concurrency safety.

2) define entities / actors
   Actors: User
   Entities: User, Node(abstract), Folder, FileNode, FileVersion, ShareEntry, TrashEntry

3) define apis - get/post/put, request, response (mirrored by controller methods)
   POST   /users                                   {name} -> {userId}
   POST   /nodes/folder                            {ownerId, parentId, name} -> {folderId}
   POST   /nodes/file                              {ownerId, parentId, name, bytes[]} -> {fileId, versionId}
   POST   /nodes/file/{fileId}/versions            {ownerId, bytes[]} -> {versionId}
   GET    /nodes/{nodeId}                          -> {metadata}
   GET    /nodes/{folderId}/children               {cursor?, limit} -> {items[], nextCursor?}
   GET    /download/{fileId}/latest                -> {bytesLength, versionId}
   POST   /share                                   {nodeId, granteeUserId, perm(VIEW|EDIT)} -> {ok}
   GET    /search                                  {userId, query} -> {nodes[]}
   PUT    /nodes/{nodeId}/rename                   {name} -> {ok}
   PUT    /nodes/{nodeId}/move                     {newParentId} -> {ok}
   DELETE /nodes/{nodeId}                          -> {trashed=true}
   POST   /trash/{nodeId}/restore                  -> {ok}
   GET    /files/{fileId}/versions                 -> [{versionId, size, createdAt}]
   POST   /files/{fileId}/restoreVersion           {versionId} -> {ok}

4) define services involved
   AuthZService        - permission checks (OWNER/EDIT/VIEW), inheritance on folders.
   TreeService         - create/move/rename/list; trash/restore; path integrity.
   FileService         - upload versions, download, version list/restore.
   ShareService        - grant/revoke sharing on nodes (propagates by traversal).
   SearchService       - simple name-based search filtered by access.
   IdGenerator         - IDs.

5) define db schema - what all tables are required, what are the columns, what are the keys
   user(id PK, name, created_at)
   node(id PK, type ENUM(FILE,FOLDER), name, owner_id FK(user), parent_id FK(node), created_at, updated_at, trashed BOOL)
   file_version(id PK, file_id FK(node), size, created_at, data BLOB)   // in prod, data in object store
   share(node_id FK, grantee_user_id FK(user), perm ENUM(VIEW,EDIT), created_at)  UNIQUE(node_id, grantee_user_id)
   // effective permission = owner OR explicit share OR inherited from any ancestor folder
*/
```

### C++ Implementation

```cpp
#include <bits/stdc++.h>
using namespace std;
/*
Template ->
1) define functional requirements
   - Create folders/files; hierarchical tree with root per user.
   - Upload file (new file or new version), download (stub returns bytes length), rename, move, delete (trash) & restore.
   - Share file/folder with users with permissions: VIEW, EDIT, OWNER (owner implicit).
   - List folder contents with pagination (cursor+limit).
   - Search by name (prefix/substring) within items user can access.
   - Version history: list versions, restore a previous version.
   - In-memory only; 40-min interview friendly; single JVM; basic concurrency safety.

2) define entities / actors
   Actors: User
   Entities: User, Node(abstract), Folder, FileNode, FileVersion, ShareEntry, TrashEntry

3) define apis - get/post/put, request, response (mirrored by controller methods)
   POST   /users                                   {name} -> {userId}
   POST   /nodes/folder                            {ownerId, parentId, name} -> {folderId}
   POST   /nodes/file                              {ownerId, parentId, name, bytes[]} -> {fileId, versionId}
   POST   /nodes/file/{fileId}/versions            {ownerId, bytes[]} -> {versionId}
   GET    /nodes/{nodeId}                          -> {metadata}
   GET    /nodes/{folderId}/children               {cursor?, limit} -> {items[], nextCursor?}
   GET    /download/{fileId}/latest                -> {bytesLength, versionId}
   POST   /share                                   {nodeId, granteeUserId, perm(VIEW|EDIT)} -> {ok}
   GET    /search                                  {userId, query} -> {nodes[]}
   PUT    /nodes/{nodeId}/rename                   {name} -> {ok}
   PUT    /nodes/{nodeId}/move                     {newParentId} -> {ok}
   DELETE /nodes/{nodeId}                          -> {trashed=true}
   POST   /trash/{nodeId}/restore                  -> {ok}
   GET    /files/{fileId}/versions                 -> [{versionId, size, createdAt}]
   POST   /files/{fileId}/restoreVersion           {versionId} -> {ok}

4) define services involved
   AuthZService        - permission checks (OWNER/EDIT/VIEW), inheritance on folders.
   TreeService         - create/move/rename/list; trash/restore; path integrity.
   FileService         - upload versions, download, version list/restore.
   ShareService        - grant/revoke sharing on nodes (propagates by traversal).
   SearchService       - simple name-based search filtered by access.
   IdGenerator         - IDs.

5) define db schema - what all tables are required, what are the columns, what are the keys
   user(id PK, name, created_at)
   node(id PK, type ENUM(FILE,FOLDER), name, owner_id FK(user), parent_id FK(node), created_at, updated_at, trashed BOOL)
   file_version(id PK, file_id FK(node), size, created_at, data BLOB)   // in prod, data in object store
   share(node_id FK, grantee_user_id FK(user), perm ENUM(VIEW,EDIT), created_at)  UNIQUE(node_id, grantee_user_id)
   // effective permission = owner OR explicit share OR inherited from any ancestor folder
*/
/* ===== Domain ===== */
enum NodeType { FILE, FOLDER }
enum Perm { VIEW, EDIT, OWNER }

const class User { const std::string id, name; const Instant createdAt=Instant.now(); User(std::string id,std::string name){this->id=id;this->name=name;} }

/** Abstract Node */
abstract class Node {
    const std::string id, ownerId;
    volatile std::string parentId; // nullptr for root
    volatile std::string name;
    const NodeType type;
    volatile boolean trashed=false;
    volatile Instant createdAt=Instant.now(), updatedAt=Instant.now();
    Node(std::string id,std::string ownerId,std::string parentId,std::string name,NodeType type){
        this->id=id; this->ownerId=ownerId; this->parentId=parentId; this->name=name; this->type=type;
    }
}
const class Folder extends Node { Folder(std::string id,std::string ownerId,std::string parentId,std::string name){ super(id,ownerId,parentId,name,NodeType.FOLDER);} }

const class FileVersion {
    const std::string id; const std::string fileId;
    const byte[] data; const int size;
    const Instant createdAt=Instant.now();
    FileVersion(std::string id,std::string fileId,byte[] data){
        this->id=id; this->fileId=fileId; this->data=data; this->size=data.length;
    }
}
const class FileNode extends Node {
    // versions newest-first at index 0
    const std::vector<FileVersion> versions = Collections.synchronizedList(std::vector<>{});
    FileNode(std::string id,std::string ownerId,std::string parentId,std::string name){ super(id,ownerId,parentId,name,NodeType.FILE); }
}

const class ShareEntry {
    const std::string nodeId; const std::string granteeUserId; const Perm perm; const Instant createdAt=Instant.now();
    ShareEntry(std::string nodeId,std::string granteeUserId,Perm perm){this->nodeId=nodeId;this->granteeUserId=granteeUserId;this->perm=perm;}
}

/* ===== Ids ===== */
class Ids { const AtomicLong n=new AtomicLong(1); std::string next(std::string p){ return p+"-"+n.getAndIncrement(); } }

/* ===== Repos (in-memory) ===== */
class UserRepo { const std::unordered_map<std::string,User> m=new ConcurrentHashMap<>(); User save(User u){m.put(u.id,u);return u;} std::optional<User> byId(std::string id){return Optional.ofNullable(m.get(id));} }
class NodeRepo {
    const std::unordered_map<std::string,Node> m=new ConcurrentHashMap<>();
    Node save(Node n){ n.updatedAt=Instant.now(); m.put(n.id,n); return n; }
    std::optional<Node> byId(std::string id){ return Optional.ofNullable(m.get(id)); }
    std::vector<Node> children(std::string parentId){
        return m.values().stream()
                .filter(n->Objects == (n.parentId,parentId))
                .sorted(Comparator.comparing((Node x)->x.type).thenComparing(x->x.name.toLowerCase()))
                .collect(Collectors.toList());
    }
}
class VersionRepo {
    const std::unordered_map<std::string,FileVersion> m=new ConcurrentHashMap<>();
    FileVersion save(FileVersion v){ m.put(v.id,v); return v; }
    std::optional<FileVersion> byId(std::string id){ return Optional.ofNullable(m.get(id)); }
}
class ShareRepo {
    // key: nodeId -> (userId -> perm)
    const std::unordered_map<std::string, std::unordered_map<std::string, ShareEntry>> m = new ConcurrentHashMap<>();
    void upsert(std::string nodeId, std::string userId, Perm perm){
        m.computeIfAbsent(nodeId,k->new ConcurrentHashMap<>()).put(userId, new ShareEntry(nodeId,userId,perm));
    }
    std::optional<ShareEntry> get(std::string nodeId, std::string userId){
        return Optional.ofNullable(m.getOrDefault(nodeId, Map.of()).get(userId));
    }
    std::unordered_map<std::string,ShareEntry> forNode(std::string nodeId){ return m.getOrDefault(nodeId, Map.of()); }
}

/* ===== Exceptions ===== */
class DomainException extends RuntimeException { DomainException(std::string msg){super(msg);} }

/* ===== Services ===== */
class AuthZService {
    const NodeRepo nodes; const ShareRepo shares;
    AuthZService(NodeRepo n, ShareRepo s){nodes=n; shares=s;}

    boolean canView(std::string userId, std::string nodeId){ return hasPerm(userId,nodeId,Perm.VIEW); }
    boolean canEdit(std::string userId, std::string nodeId){ return hasPerm(userId,nodeId,Perm.EDIT); }

    boolean hasPerm(std::string userId, std::string nodeId, Perm needed){
        Node cur = nodes.byId(nodeId).orElseThrow(()->new DomainException("node"));
        // owner is OWNER
        if (cur.ownerId == (userId)) return true;
        // explicit share
        Perm max = maxPermOnNode(userId, cur.id);
        if (permSatisfies(max, needed)) return true;
        // inherited from ancestors
        std::string pid = cur.parentId;
        while (pid != nullptr){
            Node parent = nodes.byId(pid).orElse(nullptr);
            if (parent==nullptr) break;
            max = maxPermOnNode(userId, parent.id);
            if (permSatisfies(max, needed)) return true;
            pid = parent.parentId;
        }
        return false;
    }

    Perm maxPermOnNode(std::string userId, std::string nodeId){
        return shares.get(nodeId,userId).map(e->e.perm).orElse(nullptr);
    }

    boolean permSatisfies(Perm have, Perm needed){
        if (have==nullptr) return false;
        if (have==Perm.OWNER) return true;
        if (needed==Perm.VIEW) return have==Perm.VIEW || have==Perm.EDIT;
        if (needed==Perm.EDIT) return have==Perm.EDIT; // OWNER already handled
        return false;
    }
}

class TreeService {
    const NodeRepo nodes; const Ids ids;
    TreeService(NodeRepo n, Ids ids){nodes=n; this->ids=ids;}

    synchronized Folder createFolder(std::string ownerId, std::string parentId, std::string name){
        validateParent(parentId, ownerId);
        Folder f = new Folder(ids.next("fld"), ownerId, parentId, name);
        return (Folder) nodes.save(f);
    }

    synchronized FileNode createFile(std::string ownerId, std::string parentId, std::string name, byte[] data, VersionRepo versions){
        validateParent(parentId, ownerId);
        FileNode fn = new FileNode(ids.next("fil"), ownerId, parentId, name);
        nodes.save(fn);
        // first version
        FileVersion v = new FileVersion(ids.next("ver"), fn.id, data);
        versions.save(v);
        fn.versions.add(0, v);
        return (FileNode) nodes.save(fn);
    }

    synchronized void rename(std::string userId, std::string nodeId, std::string newName){
        Node n = nodes.byId(nodeId).orElseThrow(()->new DomainException("node"));
        if (!n.ownerId == (userId)) throw new DomainException("only owner can rename (simplified)");
        n.name = newName; nodes.save(n);
    }

    synchronized void move(std::string userId, std::string nodeId, std::string newParentId){
        Node n = nodes.byId(nodeId).orElseThrow(()->new DomainException("node"));
        Node p = newParentId==nullptr?nullptr:nodes.byId(newParentId).orElseThrow(()->new DomainException("parent"));
        if (p!=nullptr && p.type!=NodeType.FOLDER) throw new DomainException("parent must be folder");
        if (!n.ownerId == (userId)) throw new DomainException("only owner can move (simplified)");
        // prevent cycles
        if (isDescendant(newParentId, n.id)) throw new DomainException("cannot move into descendant");
        n.parentId = newParentId; nodes.save(n);
    }

    synchronized void trash(std::string userId, std::string nodeId){
        Node n = nodes.byId(nodeId).orElseThrow(()->new DomainException("node"));
        if (!n.ownerId == (userId)) throw new DomainException("only owner can trash");
        markTrashedRecursive(n, true);
    }

    synchronized void restore(std::string userId, std::string nodeId){
        Node n = nodes.byId(nodeId).orElseThrow(()->new DomainException("node"));
        if (!n.ownerId == (userId)) throw new DomainException("only owner can restore");
        markTrashedRecursive(n, false);
    }

    std::vector<Node> listChildren(std::string folderId, std::string cursor, int limit){
        Node f = nodes.byId(folderId).orElseThrow(()->new DomainException("folder"));
        if (f.type!=NodeType.FOLDER) throw new DomainException("not folder");
        std::vector<Node> all = nodes.children(folderId).stream().filter(n->!n.trashed).collect(Collectors.toList());
        int start = 0;
        if (cursor!=nullptr){
            for (int i=0;i<all.size();i++) if (all.get(i).id == (cursor)) { start = i+1; break; }
        }
        return all.stream().skip(start).limit(limit).collect(Collectors.toList());
    }

    void validateParent(std::string parentId, std::string ownerId){
        if (parentId==nullptr) return;
        Node p = nodes.byId(parentId).orElseThrow(()->new DomainException("parent not found"));
        if (p.type!=NodeType.FOLDER) throw new DomainException("parent must be a folder");
        if (!p.ownerId == (ownerId)) throw new DomainException("parent not owned by creator (simplified)");
    }

    boolean isDescendant(std::string candidateParentId, std::string nodeId){
        std::string cur = candidateParentId;
        while (cur!=nullptr){
            if (cur == (nodeId)) return true;
            Node n = nodes.byId(cur).orElse(nullptr);
            cur = n==nullptr?nullptr:n.parentId;
        }
        return false;
    }

    void markTrashedRecursive(Node n, boolean val){
        n.trashed = val; nodes.save(n);
        if (n.type==NodeType.FOLDER){
            for (Node c : nodes.children(n.id)) markTrashedRecursive(c, val);
        }
    }
}

class FileService {
    const NodeRepo nodes; const VersionRepo versions; const Ids ids;
    FileService(NodeRepo n, VersionRepo v, Ids ids){nodes=n; versions=v; this->ids=ids;}

    FileVersion uploadNewVersion(std::string userId, std::string fileId, byte[] data){
        FileNode f = (FileNode) nodes.byId(fileId).orElseThrow(()->new DomainException("file"));
        if (!f.ownerId == (userId)) throw new DomainException("only owner can upload version (simplified)");
        FileVersion v = new FileVersion(ids.next("ver"), f.id, data);
        versions.save(v);
        f.versions.add(0, v);
        nodes.save(f);
        return v;
    }

    FileVersion downloadLatest(std::string userId, std::string fileId){
        FileNode f = (FileNode) nodes.byId(fileId).orElseThrow(()->new DomainException("file"));
        if (f.versions.isEmpty()) throw new DomainException("no versions");
        return f.versions.get(0);
    }

    std::vector<FileVersion> listVersions(std::string fileId){
        FileNode f = (FileNode) nodes.byId(fileId).orElseThrow(()->new DomainException("file"));
        return new std::vector<>(f.versions);
    }

    void restoreVersion(std::string userId, std::string fileId, std::string versionId){
        FileNode f = (FileNode) nodes.byId(fileId).orElseThrow(()->new DomainException("file"));
        if (!f.ownerId == (userId)) throw new DomainException("only owner can restore");
        FileVersion v = versions.byId(versionId).orElseThrow(()->new DomainException("version"));
        if (!v.fileId == (f.id)) throw new DomainException("version/file mismatch");
        // move this version to head by inserting a clone (typical GDrive restore creates new head)
        FileVersion restored = new FileVersion(ids.next("ver"), f.id, v.data);
        versions.save(restored);
        f.versions.add(0, restored);
        nodes.save(f);
    }
}

class ShareService {
    const ShareRepo shares; const NodeRepo nodes;
    ShareService(ShareRepo s, NodeRepo n){shares=s; nodes=n;}
    void share(std::string ownerId, std::string nodeId, std::string granteeUserId, Perm perm){
        Node n = nodes.byId(nodeId).orElseThrow(()->new DomainException("node"));
        if (!n.ownerId == (ownerId)) throw new DomainException("only owner can share (simplified)");
        if (perm==Perm.OWNER) throw new DomainException("cannot grant OWNER");
        shares.upsert(nodeId, granteeUserId, perm);
    }
}

class SearchService {
    const NodeRepo nodes; const AuthZService authz;
    SearchService(NodeRepo n, AuthZService a){nodes=n; authz=a;}
    std::vector<Node> search(std::string userId, std::string query){
        std::string q = query.toLowerCase();
        return nodes.m.values().stream()
                .filter(n->!n.trashed)
                .filter(n->n.name.toLowerCase().contains(q))
                .filter(n->authz.canView(userId, n.id))
                .sorted(Comparator.comparing((Node n)->n.type).thenComparing(n->n.name.toLowerCase()))
                .collect(Collectors.toList());
    }
}

/* ===== Controller Facade ===== */
class DriveController {
    const UserRepo users; const NodeRepo nodes; const VersionRepo versions;
    const AuthZService authz; const TreeService tree; const FileService fileSvc;
    const ShareService share; const SearchService search;

    DriveController(UserRepo u, NodeRepo n, VersionRepo v, AuthZService a, TreeService t, FileService f, ShareService s, SearchService srch){
        users=u; nodes=n; versions=v; authz=a; tree=t; fileSvc=f; share=s; search=srch;
    }

    User postUser(std::string name){ return users.save(new User(GDrive40Min.ids.next("u"), name)); }

    Folder postFolder(std::string ownerId, std::string parentId, std::string name){ return tree.createFolder(ownerId, parentId, name); }

    FileNode postFile(std::string ownerId, std::string parentId, std::string name, byte[] data){ return tree.createFile(ownerId, parentId, name, data, versions); }

    FileVersion postFileVersion(std::string ownerId, std::string fileId, byte[] data){
        if (!authz.canEdit(ownerId, fileId)) throw new DomainException("no edit permission");
        return fileSvc.uploadNewVersion(ownerId, fileId, data);
    }

    std::unordered_map<std::string,auto> getNode(std::string userId, std::string nodeId){
        if (!authz.canView(userId, nodeId)) throw new DomainException("no view permission");
        Node n = nodes.byId(nodeId).orElseThrow(()->new DomainException("node"));
        std::unordered_map<std::string,auto> m = std::unordered_map<>{};
        m.put("id", n.id); m.put("type", n.type.name()); m.put("name", n.name);
        m.put("ownerId", n.ownerId); m.put("parentId", n.parentId); m.put("trashed", n.trashed);
        return m;
    }

    std::unordered_map<std::string,auto> getChildren(std::string userId, std::string folderId, std::string cursor, int limit){
        if (!authz.canView(userId, folderId)) throw new DomainException("no view permission");
        std::vector<Node> items = tree.listChildren(folderId, cursor, limit);
        std::string next = items.size()==limit ? items.get(items.size()-1).id : nullptr;
        std::unordered_map<std::string,auto> out = std::unordered_map<>{};
        out.put("items", items.stream().map(n->Map.of("id",n.id,"name",n.name,"type",n.type.name())).collect(Collectors.toList()));
        out.put("nextCursor", next);
        return out;
    }

    std::unordered_map<std::string,auto> getDownloadLatest(std::string userId, std::string fileId){
        if (!authz.canView(userId, fileId)) throw new DomainException("no view permission");
        FileVersion v = fileSvc.downloadLatest(userId, fileId);
        return Map.of("versionId", v.id, "bytesLength", v.size);
    }

    void putRename(std::string userId, std::string nodeId, std::string newName){
        if (!authz.canEdit(userId, nodeId) && !nodes.byId(nodeId).orElseThrow().ownerId == (userId))
            throw new DomainException("no edit permission");
        tree.rename(userId, nodeId, newName);
    }

    void putMove(std::string userId, std::string nodeId, std::string newParentId){
        if (!nodes.byId(nodeId).orElseThrow().ownerId == (userId))
            throw new DomainException("only owner can move");
        tree.move(userId, nodeId, newParentId);
    }

    void deleteNode(std::string userId, std::string nodeId){
        if (!nodes.byId(nodeId).orElseThrow().ownerId == (userId))
            throw new DomainException("only owner can trash");
        tree.trash(userId, nodeId);
    }

    void postRestore(std::string userId, std::string nodeId){ tree.restore(userId, nodeId); }

    void postShare(std::string ownerId, std::string nodeId, std::string granteeUserId, Perm perm){ share.share(ownerId, nodeId, granteeUserId, perm); }

    std::vector<Node> getSearch(std::string userId, std::string query){ return search.search(userId, query); }

    std::vector<std::unordered_map<std::string,auto>> getVersions(std::string userId, std::string fileId){
        if (!authz.canView(userId, fileId)) throw new DomainException("no view permission");
        return fileSvc.listVersions(fileId).stream().map(v->Map.of("versionId",v.id,"size",v.size,"createdAt",v.createdAt)).collect(Collectors.toList());
    }

    void postRestoreVersion(std::string ownerId, std::string fileId, std::string versionId){
        if (!authz.canEdit(ownerId, fileId)) throw new DomainException("no edit permission");
        fileSvc.restoreVersion(ownerId, fileId, versionId);
    }
}

/* ===== Demo (tiny, 40-min friendly) ===== */
class GDrive40Min {
    static const Ids ids = new Ids();

    int main() {
        // Repos
        UserRepo users = new UserRepo();
        NodeRepo nodes = new NodeRepo();
        VersionRepo versions = new VersionRepo();
        ShareRepo shares = new ShareRepo();

        // Services
        AuthZService authz = new AuthZService(nodes, shares);
        TreeService tree = new TreeService(nodes, ids);
        FileService fileSvc = new FileService(nodes, versions, ids);
        ShareService shareSvc = new ShareService(shares, nodes);
        SearchService searchSvc = new SearchService(nodes, authz);

        DriveController api = new DriveController(users, nodes, versions, authz, tree, fileSvc, shareSvc, searchSvc);

        // Users
        User alice = api.postUser("Alice");
        User bob   = api.postUser("Bob");

        // Root (nullptr parent) and basic structure for Alice
        Folder root = api.postFolder(alice.id, nullptr, "Alice Root");
        Folder docs = api.postFolder(alice.id, root.id, "Docs");
        Folder pics = api.postFolder(alice.id, root.id, "Pictures");

        // Upload a file
        FileNode spec = api.postFile(alice.id, docs.id, "DesignSpec.md", "v1 design".getBytes());
        std::cout << "Uploaded file: "+spec.id+" latest="+api.getDownloadLatest(alice.id, spec.id)) << std::endl;

        // New version
        api.postFileVersion(alice.id, spec.id, "v2 design (added API)".getBytes());
        std::cout << "Versions: "+api.getVersions(alice.id, spec.id)) << std::endl;

        // Share with Bob as VIEW
        api.postShare(alice.id, docs.id, bob.id, Perm.VIEW);

        // Bob lists Docs
        std::cout << "Bob children of Docs: "+api.getChildren(bob.id, docs.id, nullptr, 10)) << std::endl;

        // Search
        std::cout << "Search 'Design' as Bob: "+api.getSearch(bob.id, "Design")) << std::endl;

        // Rename & move (owner only)
        api.putRename(alice.id, spec.id, "DesignSpec_v2.md");
        api.putMove(alice.id, spec.id, pics.id);

        // Trash & restore
        api.deleteNode(alice.id, pics.id);
        std::cout << "After trash, children root: "+api.getChildren(alice.id, root.id, nullptr, 10)) << std::endl;
        api.postRestore(alice.id, pics.id);
        std::cout << "After restore, children root: "+api.getChildren(alice.id, root.id, nullptr, 10)) << std::endl;
    }
}
```

## Instagram Feed

```
/*
Template ->
1) define functional requirements
   - Users can follow/unfollow others.
   - Users create posts with media + caption; like/comment a post.
   - Generate home feed for a user from followed users’ posts.
   - Ranking = recency + lightweight engagement (likes/comments) signal.
   - Pagination with cursor (createdAt + postId).
   - Simple fan-out-on-read (compute feed on request), add basic cache with TTL.
   - In-memory, thread-safe where needed; doable in ~40 minutes.

2) define entities / actors
   Actors: User (viewer/creator)
   Entities: User, Post, Like, Comment, FollowEdge, FeedEntry (cached)

3) define apis - get/post/put, request, response
   POST   /users                             {username} -> {userId}
   POST   /users/{id}/follow                 {targetUserId} -> {status}
   DELETE /users/{id}/follow                 {targetUserId} -> {status}
   POST   /posts                             {authorId, caption, mediaUrl?} -> {postId}
   POST   /posts/{id}/like                   {userId} -> {likes}
   POST   /posts/{id}/comment                {userId, text} -> {commentId}
   GET    /feed                              {userId, cursor?, limit} -> {items:[...], nextCursor?}

4) define services involved
   UserService        - create users, follow/unfollow.
   PostService        - create posts; like/comment; read post stats.
   GraphService       - read follow graph (who I follow).
   FeedService        - build/rank/paginate feed; small cache with TTL.
   IdGenerator        - generate IDs.

5) define db schema - what all tables are required, what are the columns, what are the keys
   user(id PK, username UNIQUE, created_at)
   follow(user_id FK, target_user_id FK, created_at)  UNIQUE(user_id, target_user_id)
   post(id PK, author_id FK, caption, media_url, created_at)
   like(id PK, post_id FK, user_id FK, created_at)    UNIQUE(post_id, user_id)
   comment(id PK, post_id FK, user_id FK, text, created_at)
   (feed cache not persisted: user_id -> [post_id, score, cached_at])
*/
```

### C++ Implementation

```cpp
#include <bits/stdc++.h>
using namespace std;
/*
Template ->
1) define functional requirements
   - Users can follow/unfollow others.
   - Users create posts with media + caption; like/comment a post.
   - Generate home feed for a user from followed users’ posts.
   - Ranking = recency + lightweight engagement (likes/comments) signal.
   - Pagination with cursor (createdAt + postId).
   - Simple fan-out-on-read (compute feed on request), add basic cache with TTL.
   - In-memory, thread-safe where needed; doable in ~40 minutes.

2) define entities / actors
   Actors: User (viewer/creator)
   Entities: User, Post, Like, Comment, FollowEdge, FeedEntry (cached)

3) define apis - get/post/put, request, response
   POST   /users                             {username} -> {userId}
   POST   /users/{id}/follow                 {targetUserId} -> {status}
   DELETE /users/{id}/follow                 {targetUserId} -> {status}
   POST   /posts                             {authorId, caption, mediaUrl?} -> {postId}
   POST   /posts/{id}/like                   {userId} -> {likes}
   POST   /posts/{id}/comment                {userId, text} -> {commentId}
   GET    /feed                              {userId, cursor?, limit} -> {items:[...], nextCursor?}

4) define services involved
   UserService        - create users, follow/unfollow.
   PostService        - create posts; like/comment; read post stats.
   GraphService       - read follow graph (who I follow).
   FeedService        - build/rank/paginate feed; small cache with TTL.
   IdGenerator        - generate IDs.

5) define db schema - what all tables are required, what are the columns, what are the keys
   user(id PK, username UNIQUE, created_at)
   follow(user_id FK, target_user_id FK, created_at)  UNIQUE(user_id, target_user_id)
   post(id PK, author_id FK, caption, media_url, created_at)
   like(id PK, post_id FK, user_id FK, created_at)    UNIQUE(post_id, user_id)
   comment(id PK, post_id FK, user_id FK, text, created_at)
   (feed cache not persisted: user_id -> [post_id, score, cached_at])
*/
/* ===== Domain ===== */
const class User { const std::string id, username; const Instant createdAt=Instant.now(); User(std::string id,std::string u){this->id=id;this->username=u;} }

const class Post {
    const std::string id, authorId, caption, mediaUrl; const Instant createdAt=Instant.now();
    const std::unordered_set<std::string> likes = ConcurrentHashMap.newKeySet();
    const std::vector<Comment> comments = Collections.synchronizedList(std::vector<>{});
    Post(std::string id, std::string authorId, std::string caption, std::string mediaUrl){
        this->id=id; this->authorId=authorId; this->caption=caption; this->mediaUrl=mediaUrl;
    }
}
const class Comment { const std::string id, postId, userId, text; const Instant createdAt=Instant.now();
    Comment(std::string id,std::string postId,std::string userId,std::string text){this->id=id;this->postId=postId;this->userId=userId;this->text=text;}
}
const class FollowEdge { const std::string userId, targetUserId; const Instant createdAt=Instant.now();
    FollowEdge(std::string u,std::string t){this->userId=u;this->targetUserId=t;}
}

/* ===== Ids ===== */
class Ids { const AtomicLong n=new AtomicLong(1); std::string next(std::string p){ return p+"-"+n.getAndIncrement(); } }

/* ===== Repos (in-memory) ===== */
class UserRepo {
    const std::unordered_map<std::string,User> byId = new ConcurrentHashMap<>();
    const std::unordered_map<std::string,std::string> byUsername = new ConcurrentHashMap<>();
    User save(User u){ byId.put(u.id,u); byUsername.put(u.username,u.id); return u; }
    std::optional<User> byId(std::string id){ return Optional.ofNullable(byId.get(id)); }
    std::optional<User> byUsername(std::string uname){ return Optional.ofNullable(byUsername.get(uname)).map(byId::get); }
}

class FollowRepo {
    // adjacency list: follower -> set of followees
    const std::unordered_map<std::string, std::unordered_set<std::string>> out = new ConcurrentHashMap<>();
    boolean follow(std::string userId, std::string targetId){
        out.computeIfAbsent(userId,k->ConcurrentHashMap.newKeySet());
        return out.get(userId).add(targetId);
    }
    boolean unfollow(std::string userId, std::string targetId){
        return out.getOrDefault(userId, Set.of()).remove(targetId);
    }
    std::unordered_set<std::string> following(std::string userId){
        return new std::unordered_set<>(out.getOrDefault(userId, Set.of()));
    }
}

class PostRepo {
    const std::unordered_map<std::string,Post> byId = new ConcurrentHashMap<>();
    // author -> posts sorted newest first (we’ll keep as list and sort on read for simplicity)
    const std::unordered_map<std::string,std::vector<Post>> byAuthor = new ConcurrentHashMap<>();

    Post save(Post p){
        byId.put(p.id,p);
        byAuthor.computeIfAbsent(p.authorId,k->Collections.synchronizedList(std::vector<>{})).add(p);
        return p;
    }
    std::optional<Post> byId(std::string id){ return Optional.ofNullable(byId.get(id)); }
    std::vector<Post> byAuthors(std::unordered_set<std::string> authorIds){
        std::vector<Post> all = std::vector<>{};
        for (std::string a: authorIds) {
            all.addAll(byAuthor.getOrDefault(a, List.of()));
        }
        // newest first
        all.sort(Comparator.comparing((Post x)->x.createdAt).reversed().thenComparing(x->x.id));
        return all;
    }
}

/* ===== Services ===== */
class UserService {
    const UserRepo users; const FollowRepo follows; const Ids ids;
    UserService(UserRepo u, FollowRepo f, Ids ids){users=u;follows=f;this->ids=ids;}
    User create(std::string username){
        if (users.byUsername(username).isPresent()) throw new RuntimeException("username taken");
        return users.save(new User(ids.next("u"), username));
    }
    boolean follow(std::string userId, std::string target){ if (userId == (target)) return false; return follows.follow(userId, target); }
    boolean unfollow(std::string userId, std::string target){ return follows.unfollow(userId, target); }
    std::unordered_set<std::string> following(std::string userId){ return follows.following(userId); }
}

class PostService {
    const PostRepo posts; const Ids ids;
    PostService(PostRepo p, Ids ids){posts=p; this->ids=ids;}
    Post create(std::string authorId, std::string caption, std::string mediaUrl){ return posts.save(new Post(ids.next("p"), authorId, caption, mediaUrl)); }
    int like(std::string postId, std::string userId){
        Post p = posts.byId(postId).orElseThrow(()->new RuntimeException("post not found"));
        p.likes.add(userId); return p.likes.size();
    }
    Comment comment(std::string postId, std::string userId, std::string text){
        Post p = posts.byId(postId).orElseThrow(()->new RuntimeException("post not found"));
        Comment c = new Comment(ids.next("c"), postId, userId, text);
        p.comments.add(c); return c;
    }
    std::optional<Post> byId(std::string id){ return posts.byId(id); }
    std::vector<Post> postsForAuthors(std::unordered_set<std::string> authors){ return posts.byAuthors(authors); }
}

/* ===== Feed Cache ===== */
const class FeedEntry { const std::string postId; const double score; const Instant cachedAt=Instant.now(); FeedEntry(std::string id,double s){postId=id;score=s;} }

class FeedCache {
    // userId -> (entries sorted desc by score); plus cursor material
    static const long TTL_SEC = 60; // small TTL
    const std::unordered_map<std::string, std::vector<FeedEntry>> cache = new ConcurrentHashMap<>();
    const std::unordered_map<std::string, Instant> createdAt = new ConcurrentHashMap<>();

    std::optional<std::vector<FeedEntry>> get(std::string userId){
        Instant ts = createdAt.get(userId);
        if (ts==nullptr) return Optional.empty();
        if (Instant.now().isAfter(ts.plusSeconds(TTL_SEC))) { invalidate(userId); return Optional.empty(); }
        return Optional.of(cache.getOrDefault(userId, List.of()));
    }
    void put(std::string userId, std::vector<FeedEntry> entries){
        cache.put(userId, entries); createdAt.put(userId, Instant.now());
    }
    void invalidate(std::string userId){ cache.remove(userId); createdAt.remove(userId); }
}

/* ===== Feed Service ===== */
class FeedService {
    const UserService users; const PostService posts; const FeedCache cache;

    FeedService(UserService u, PostService p, FeedCache cache){users=u; posts=p; this->cache=cache;}

    static const class FeedItem {
        const std::string postId, authorId, caption, mediaUrl;
        const Instant createdAt; const int likeCount; const int commentCount; const double score;
        FeedItem(Post p, double score){
            this->postId=p.id; this->authorId=p.authorId; this->caption=p.caption; this->mediaUrl=p.mediaUrl;
            this->createdAt=p.createdAt; this->likeCount=p.likes.size(); this->commentCount=p.comments.size(); this->score=score;
        }
        std::string toString(){ return std::string.format("{post=%s by=%s likes=%d comments=%d score=%.2f}", postId, authorId, likeCount, commentCount, score); }
    }

    // Rank = w1 * freshness + w2 * likes + w3 * comments
    double score(Post p){
        double hours = Math.max(0.0, Duration.between(p.createdAt, Instant.now()).toMinutes()/60.0);
        double recency = 1.0 / (1.0 + hours);               // decays with time
        double likeBoost = Math.log(1 + p.likes.size());     // diminishing returns
        double commentBoost = 1.5 * Math.log(1 + p.comments.size());
        return 0.7*recency + 0.2*likeBoost + 0.1*commentBoost;
    }

    // Build or read cached feed, then paginate by cursor (createdAt|postId).
    std::vector<FeedItem> getFeed(std::string userId, std::string cursor, int limit){
        std::vector<FeedEntry> entries = cache.get(userId).orElseGet(() -> {
            std::unordered_set<std::string> authors = users.following(userId);
            if (authors.isEmpty()) authors = Set.of(userId); // fallback to self posts
            std::vector<Post> candidates = posts.postsForAuthors(authors);
            std::vector<FeedEntry> ranked = candidates.stream()
                    .map(p -> new FeedEntry(p.id, score(p)))
                    .sorted(Comparator.comparingDouble((FeedEntry e)->e.score).reversed()
                            .thenComparing(e->posts.byId(e.postId).get().createdAt, Comparator.reverseOrder())
                            .thenComparing(e->e.postId))
                    .collect(Collectors.toList());
            cache.put(userId, ranked);
            return ranked;
        });

        // Cursor decoding: createdAt|postId of last item returned previously.
        Instant afterCreated = nullptr; std::string afterPostId = nullptr;
        if (cursor != nullptr && cursor.contains("|")) {
            std::string[] parts = cursor.split("\\|", 2);
            afterCreated = Instant.ofEpochMilli(long long.parseLong(parts[0]));
            afterPostId = parts[1];
        }

        std::vector<FeedItem> out = std::vector<>{};
        int collected = 0;
        for (FeedEntry e : entries) {
            Post p = posts.byId(e.postId).orElse(nullptr);
            if (p==nullptr) continue;
            if (afterCreated!=nullptr){
                // skip until we pass the cursor (compare by createdAt desc then postId)
                int cmp = p.createdAt.compareTo(afterCreated);
                if (cmp==0 && p.id == (afterPostId)) { continue; } // exact cursor
                if (cmp>0) { // p is newer than cursor; skip because we already served it earlier (descending order)
                    continue;
                }
            }
            out.add(new FeedItem(p, e.score));
            if (++collected >= Math.max(1, limit)) break;
        }
        return out;
    }

    std::string nextCursor(std::vector<FeedItem> page){
        if (page.isEmpty()) return nullptr;
        FeedItem last = page.get(page.size()-1);
        return last.createdAt.toEpochMilli() + "|" + last.postId;
    }

    void invalidate(std::string userId){ cache.invalidate(userId); }
}

/* ===== Controller (API Facade) ===== */
class FeedController {
    const UserService users; const PostService posts; const FeedService feed;

    FeedController(UserService u, PostService p, FeedService f){users=u;posts=p;feed=f;}

    // Users
    User postUser(std::string username){ return users.create(username); }
    boolean postFollow(std::string userId, std::string target){ boolean ok=users.follow(userId,target); feed.invalidate(userId); return ok; }
    boolean deleteFollow(std::string userId, std::string target){ boolean ok=users.unfollow(userId,target); feed.invalidate(userId); return ok; }

    // Posts
    Post postCreate(std::string authorId, std::string caption, std::string mediaUrl){ Post p=posts.create(authorId, caption, mediaUrl); feed.invalidate(authorId); return p; }
    int postLike(std::string postId, std::string userId){ int c=posts.like(postId, userId); return c; }
    Comment postComment(std::string postId, std::string userId, std::string text){ return posts.comment(postId, userId, text); }

    // Feed
    std::unordered_map<std::string,auto> getFeed(std::string userId, std::string cursor, int limit){
        std::vector<FeedService.FeedItem> items = feed.getFeed(userId, cursor, limit);
        std::string next = feed.nextCursor(items);
        std::unordered_map<std::string,auto> m = std::unordered_map<>{};
        m.put("items", items);
        m.put("nextCursor", next);
        return m;
    }
}

/* ===== Demo (tiny) ===== */
class InstagramFeed40Min {
    int main() {
        Ids ids = new Ids();
        UserRepo userRepo = new UserRepo();
        FollowRepo followRepo = new FollowRepo();
        PostRepo postRepo = new PostRepo();

        UserService userSvc = new UserService(userRepo, followRepo, ids);
        PostService postSvc = new PostService(postRepo, ids);
        FeedCache cache = new FeedCache();
        FeedService feedSvc = new FeedService(userSvc, postSvc, cache);
        FeedController api = new FeedController(userSvc, postSvc, feedSvc);

        // Users
        User alice = api.postUser("alice");
        User bob   = api.postUser("bob");
        User carol = api.postUser("carol");

        // Graph
        api.postFollow(alice.id, bob.id);
        api.postFollow(alice.id, carol.id);

        // Posts
        Post p1 = api.postCreate(bob.id, "Sunset at the beach", "http://img/1.jpg");
        Thread.sleep(10);
        Post p2 = api.postCreate(carol.id, "Coffee ☕️", nullptr);
        Thread.sleep(10);
        Post p3 = api.postCreate(bob.id, "Morning run 5k", nullptr);

        // Engagement to influence ranking
        api.postLike(p1.id, alice.id);
        api.postLike(p1.id, carol.id);
        api.postComment(p2.id, alice.id, "Looks great!");
        api.postLike(p3.id, alice.id);

        // Feed page 1
        std::unordered_map<std::string,auto> page1 = api.getFeed(alice.id, nullptr, 2);
        std::cout << "FEED page1: " + page1.get("items")) << std::endl;
        std::string cursor = (std::string) page1.get("nextCursor");

        // Feed page 2
        std::unordered_map<std::string,auto> page2 = api.getFeed(alice.id, cursor, 2);
        std::cout << "FEED page2: " + page2.get("items")) << std::endl;
    }
}
```

## Meeting Scheduler

```
/*
Template ->
1) define functional requirements
   - Schedule meetings between participants with date/time/duration.
   - Check participants’ availability across their calendars.
   - Book meeting room/resource if needed.
   - Update/cancel meeting, notify attendees.
   - Query list of meetings for a user.
   - In-memory, concurrency-light, simple design for 40-min interview.

2) define entities / actors
   Actors: User, CalendarService (integration stub)
   Entities: User, Meeting, MeetingRoom, Invitation

3) define apis - get/post/put, request, response
   GET  /users/{id}/meetings?day=2025-08-21
        -> [{meetingId, start, end, participants}]
   POST /meetings
        {organizerId, participantIds:[...], start, end, roomId?}
        -> {meetingId, status}
   PUT  /meetings/{id}
        {start?, end?, roomId?} -> {status}
   DELETE /meetings/{id}
        -> {status}
   POST /meetings/{id}/cancel
        -> {status}

4) define services involved
   AvailabilityService  - check if users/rooms free in requested slot.
   MeetingService       - create/update/cancel meetings.
   NotificationService  - (stub) notify participants.
   RoomService          - manage meeting rooms.
   IdGenerator          - generate IDs.

5) define db schema - what all tables are required, what are the columns, what are the keys
   user(id PK, name, email)
   meeting(id PK, organizer_id FK, start_at, end_at, room_id FK NULL, status)
   meeting_participant(meeting_id FK, user_id FK, response ENUM)
   meeting_room(id PK, name, capacity)
*/
```

### C++ Implementation

```cpp
#include <bits/stdc++.h>
using namespace std;
/*
Template ->
1) define functional requirements
   - Schedule meetings between participants with date/time/duration.
   - Check participants’ availability across their calendars.
   - Book meeting room/resource if needed.
   - Update/cancel meeting, notify attendees.
   - Query list of meetings for a user.
   - In-memory, concurrency-light, simple design for 40-min interview.

2) define entities / actors
   Actors: User, CalendarService (integration stub)
   Entities: User, Meeting, MeetingRoom, Invitation

3) define apis - get/post/put, request, response
   GET  /users/{id}/meetings?day=2025-08-21
        -> [{meetingId, start, end, participants}]
   POST /meetings
        {organizerId, participantIds:[...], start, end, roomId?}
        -> {meetingId, status}
   PUT  /meetings/{id}
        {start?, end?, roomId?} -> {status}
   DELETE /meetings/{id}
        -> {status}
   POST /meetings/{id}/cancel
        -> {status}

4) define services involved
   AvailabilityService  - check if users/rooms free in requested slot.
   MeetingService       - create/update/cancel meetings.
   NotificationService  - (stub) notify participants.
   RoomService          - manage meeting rooms.
   IdGenerator          - generate IDs.

5) define db schema - what all tables are required, what are the columns, what are the keys
   user(id PK, name, email)
   meeting(id PK, organizer_id FK, start_at, end_at, room_id FK NULL, status)
   meeting_participant(meeting_id FK, user_id FK, response ENUM)
   meeting_room(id PK, name, capacity)
*/
/* ===== Domain ===== */
enum MeetingStatus { SCHEDULED, CANCELLED }

const class User { const std::string id, name, email; User(std::string id,std::string n,std::string e){this->id=id;name=n;email=e;} }
const class MeetingRoom { const std::string id, name; const int capacity; MeetingRoom(std::string id,std::string n,int c){this->id=id;name=n;capacity=c;} }
const class Meeting {
    const std::string id, organizerId; const std::unordered_set<std::string> participants; const std::string roomId;
    volatile LocalDateTime start, end; volatile MeetingStatus status=MeetingStatus.SCHEDULED;
    Meeting(std::string id,std::string org,std::unordered_set<std::string> parts,LocalDateTime s,LocalDateTime e,std::string roomId){
        this->id=id;this->organizerId=org;this->participants=parts;this->start=s;this->end=e;this->roomId=roomId;
    }
}

/* ===== Repos ===== */
class Ids { const AtomicLong n=new AtomicLong(1); std::string next(std::string p){return p+"-"+n.getAndIncrement();} }
class UserRepo { const std::unordered_map<std::string,User> m=new ConcurrentHashMap<>(); User save(User u){m.put(u.id,u);return u;} std::optional<User> byId(std::string id){return Optional.ofNullable(m.get(id));} }
class RoomRepo { const std::unordered_map<std::string,MeetingRoom> m=new ConcurrentHashMap<>(); MeetingRoom save(MeetingRoom r){m.put(r.id,r);return r;} std::optional<MeetingRoom> byId(std::string id){return Optional.ofNullable(m.get(id));} }
class MeetingRepo {
    const std::unordered_map<std::string,Meeting> m=new ConcurrentHashMap<>();
    Meeting save(Meeting x){m.put(x.id,x);return x;}
    std::optional<Meeting> byId(std::string id){return Optional.ofNullable(m.get(id));}
    std::vector<Meeting> byUserAndDay(std::string uid, LocalDate d){
        return m.values().stream()
            .filter(mt->mt.participants.contains(uid) || mt.organizerId == (uid))
            .filter(mt->mt.start.toLocalDate() == (d))
            .collect(Collectors.toList());
    }
}

/* ===== Services ===== */
class AvailabilityService {
    const MeetingRepo meetings;
    AvailabilityService(MeetingRepo m){meetings=m;}
    boolean isUserAvailable(std::string uid, LocalDateTime s, LocalDateTime e){
        return meetings.m.values().stream()
            .filter(mt->(mt.participants.contains(uid) || mt.organizerId == (uid)) && mt.status==MeetingStatus.SCHEDULED)
            .noneMatch(mt->overlap(mt.start, mt.end, s, e));
    }
    boolean overlap(LocalDateTime s1, LocalDateTime e1, LocalDateTime s2, LocalDateTime e2){
        return !e1.isBefore(s2) && !e2.isBefore(s1);
    }
}
class MeetingService {
    const MeetingRepo meetings; const AvailabilityService avail; const Ids ids;
    MeetingService(MeetingRepo m, AvailabilityService a, Ids ids){meetings=m;avail=a;this->ids=ids;}
    Meeting schedule(std::string org, std::unordered_set<std::string> parts, LocalDateTime s, LocalDateTime e, std::string roomId){
        // check availability
        if (!avail.isUserAvailable(org,s,e)) throw new RuntimeException("Organizer busy");
        for (std::string u: parts) if (!avail.isUserAvailable(u,s,e)) throw new RuntimeException("User busy: "+u);
        Meeting mt = new Meeting(ids.next("mt"), org, parts, s, e, roomId);
        return meetings.save(mt);
    }
    Meeting update(std::string id, LocalDateTime ns, LocalDateTime ne, std::string roomId){
        Meeting mt = meetings.byId(id).orElseThrow(()->new RuntimeException("not found"));
        mt.start=ns!=nullptr?ns:mt.start; mt.end=ne!=nullptr?ne:mt.end;
        mt.status=MeetingStatus.SCHEDULED;
        return meetings.save(mt);
    }
    void cancel(std::string id){
        meetings.byId(id).ifPresent(mt->mt.status=MeetingStatus.CANCELLED);
    }
}

/* ===== Controller Facade ===== */
class MeetingController {
    const MeetingService service; const MeetingRepo repo;
    MeetingController(MeetingService s, MeetingRepo r){service=s;repo=r;}
    std::vector<Meeting> getUserMeetings(std::string uid, LocalDate d){ return repo.byUserAndDay(uid,d); }
    Meeting postMeeting(std::string org, std::unordered_set<std::string> parts, LocalDateTime s, LocalDateTime e, std::string roomId){ return service.schedule(org,parts,s,e,roomId); }
    Meeting putMeeting(std::string id, LocalDateTime ns, LocalDateTime ne, std::string roomId){ return service.update(id,ns,ne,roomId); }
    void deleteMeeting(std::string id){ service.cancel(id); }
}

/* ===== Demo ===== */
class MeetingScheduler40Min {
    int main() {
        Ids ids = new Ids();
        UserRepo users = new UserRepo();
        RoomRepo rooms = new RoomRepo();
        MeetingRepo meetings = new MeetingRepo();
        AvailabilityService avail = new AvailabilityService(meetings);
        MeetingService svc = new MeetingService(meetings, avail, ids);
        MeetingController api = new MeetingController(svc, meetings);

        User u1 = users.save(new User(ids.next("u"), "Alice","a@x.com"));
        User u2 = users.save(new User(ids.next("u"), "Bob","b@x.com"));
        rooms.save(new MeetingRoom(ids.next("room"), "Conf A", 6));

        Meeting m1 = api.postMeeting(u1.id, Set.of(u2.id), LocalDateTime.now().plusHours(1), LocalDateTime.now().plusHours(2), nullptr);
        std::cout << "Scheduled meeting: "+m1.id+" participants="+m1.participants) << std::endl;

        std::cout << "Meetings for Bob today: "+api.getUserMeetings(u2.id, LocalDate.now())) << std::endl;

        api.deleteMeeting(m1.id);
        std::cout << "Cancelled meeting. Status="+meetings.byId(m1.id).get().status) << std::endl;
    }
}
```