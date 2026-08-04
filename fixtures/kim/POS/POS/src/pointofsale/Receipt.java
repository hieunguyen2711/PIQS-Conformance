/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package pointofsale;

/**
 *
 * @author kim2
 */
import java.text.DecimalFormat;
import java.util.Date;
import java.util.List;

public class Receipt {
    private Sale sale;
    private Payment payment;
    private Date date;
    private DecimalFormat df = new DecimalFormat("$##.00");
    
    public Receipt(Sale sale, Payment payment) {
        this.sale = sale;
        this.payment = payment;
        this.date = new Date();
    }
    
    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("\n=== RECEIPT ===\n");
        sb.append("Date: ").append(date).append("\n\n");
        sb.append("Items:\n");
        sb.append("--------------------------------\n");
        
        List<SaleLineItem> items = sale.getSaleLineItem();
        for (SaleLineItem item : items) {
            sb.append(String.format("%-15s %s\n", 
                item.getItemName(),
                df.format(item.getSubTotal())));
        }
        
        sb.append("--------------------------------\n");
        sb.append(String.format("Total: %s\n", df.format(payment.amount)));
        sb.append(String.format("Payment Method: %s\n", 
            payment instanceof ByCash ? "Cash" : "Credit Card"));
        
        return sb.toString();
    }
}
